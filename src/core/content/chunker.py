import re
from typing import Any
from uuid import UUID

import tiktoken

from src.infra.data.data_repository import DataRepository
from src.infra.decorators import generic_error_handler
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.logger import configure_logging, get_logger
from src.infra.settings import get_settings
from src.models.content_models import Chunk, Document
from src.services.data_service import DataService

logger = get_logger()

settings = get_settings()


class MarkdownChunker:
    """Processes markdown, removes boilerplate, images, and creates chunks."""

    def __init__(
        self,
        max_tokens: int = 512,
        soft_token_limit: int = 400,
        min_chunk_size: int = 100,
        overlap_percentage: float = 0.05,
        save: bool = False,
        document_batch_size: int = 50,
        chunk_batch_size: int = 500,
    ):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens  # Hard limit
        self.soft_token_limit = soft_token_limit  # Soft limit
        self.min_chunk_size = min_chunk_size  # Minimum chunk size in tokens
        self.overlap_percentage = overlap_percentage  # 5% overlap
        self.document_batch_size = document_batch_size
        self.chunk_batch_size = chunk_batch_size

        # Precompile regex patterns for performance
        self.boilerplate_patterns = [
            r"^English$",  # Matches the language selection
            r"^Search\.\.\.$",
            r"^Ctrl K$",
            r"^Search$",
            r"^Navigation$",
            r"^\[.*\]\(/.*\)$",  # Matches navigation links
            r"^On this page$",
            r"^\* \* \*$",  # Matches horizontal rules used as separators
        ]
        self.boilerplate_regex = re.compile("|".join(self.boilerplate_patterns), re.MULTILINE)
        self.h_pattern = re.compile(r"^\s*(?![-*]{3,})(#{1,3})\s*(.*)$", re.MULTILINE)
        self.code_block_start_pattern = re.compile(r"^(```|~~~)(.*)$")
        self.inline_code_pattern = re.compile(r"`([^`\n]+)`")

    # Batching operations
    def batch_documents(self, documents: list[Document]) -> list[list[Document]]:
        """Batch documents into smaller chunks."""
        return [documents[i : i + self.document_batch_size] for i in range(0, len(documents), self.document_batch_size)]

    def batch_chunks(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        """Batch chunks into smaller chunks."""
        return [chunks[i : i + self.chunk_batch_size] for i in range(0, len(chunks), self.chunk_batch_size)]

    # Pre-processing operations
    @generic_error_handler
    def remove_images(self, content: str) -> str:
        """
        Remove various forms of image links and tags from a given content string.

        Args:
            content (str): The text content possibly containing image links and tags.

        Returns:
            str: The content with all image links and tags removed.

        Raises:
            Exception: Raised if there are any issues during the execution of the function.
        """
        # Remove HTML img tags (in case any slipped through from FireCrawl)
        content = re.sub(r"<img[^>]+>", "", content)

        # Remove Markdown image syntax
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

        # Remove reference-style images
        content = re.sub(r"^\[.*?\]:\s*http.*$", "", content, flags=re.MULTILINE)

        # Remove base64 encoded images
        content = re.sub(r"!\[.*?\]\(data:image/[^;]+;base64,[^\)]+\)", "", content)

        # Remove any remaining image links that might not have been caught
        content = re.sub(
            r"\[.*?\]:\s*\S*\.(png|jpg|jpeg|gif|svg|webp)", "", content, flags=re.MULTILINE | re.IGNORECASE
        )

        return content

    @generic_error_handler
    def remove_boilerplate(self, content: str) -> str:
        """
        Remove boilerplate text from the given content.

        Args:
            content (str): The content from which to remove the boilerplate text.

        Returns:
            str: The content with the boilerplate text removed and extra newlines cleaned up.

        Raises:
            AssertionError: If content is not of type str.
        """
        # Use precompiled regex
        cleaned_content = self.boilerplate_regex.sub("", content)
        # Remove any extra newlines left after removing boilerplate
        cleaned_content = re.sub(r"\n{2,}", "\n\n", cleaned_content)
        return cleaned_content.strip()

    @generic_error_handler
    def clean_header_text(self, header_text: str) -> str:
        """
        Clean header text by removing specific markdown and zero-width spaces.

        Args:
            header_text (str): The text to be cleaned.

        Returns:
            str: The cleaned header text.

        Raises:
            ValueError: If `header_text` is not a string.
        """
        # Remove zero-width spaces
        cleaned_text = header_text.replace("\u200b", "")
        # Remove markdown links but keep the link text
        cleaned_text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned_text)
        # Remove images in headers
        cleaned_text = re.sub(r"!\[.*?\]\(.*?\)", "", cleaned_text)
        cleaned_text = cleaned_text.strip()
        # Ensure shell interface are not mistaken as headers
        if cleaned_text.startswith("!/") or cleaned_text.startswith("#!"):
            cleaned_text = ""  # Empty out any shell interface mistaken as headers
        return cleaned_text

    # Main processing operations
    @generic_error_handler
    def process_documents(self, documents: list[Document]) -> list[Chunk]:
        """
        High-level pipeline to process a list of Documents into Chunks.

        1) Skip empty docs
        2) Preprocess (remove boilerplate, images)
        3) Identify sections
        4) Create chunks (calls self.create_chunks)
        5) Post-process chunks
        6) Validate
        7) Return list of all chunks
        """
        processed_chunks: list[Chunk] = []

        for document in documents:
            # 1) Skip empty doc
            logger.info(f"Processing document: {document.document_id}")
            if not document.content.strip():
                logger.warning(f"Empty content in document {document.document_id}, URL: {document.metadata.source_url}")
                continue

            # 2) Preprocess
            cleaned_content = self.remove_boilerplate(document.content)
            cleaned_content = self.remove_images(cleaned_content)
            logger.debug(f"Cleaned document {document.document_id}: {len(cleaned_content)} chars")

            # 3) Identify sections (returns intermediate data structures)
            sections = self.identify_sections(
                page_content=cleaned_content, page_metadata=document.metadata.model_dump()
            )
            logger.info("Broke down into sections")

            # 4) Create chunks
            #    Refactor create_chunks so it returns actual Chunk objects
            #    and handle references to document.source_id, etc.
            chunks = self.create_chunks(sections, document)
            logger.info(f"Created {len(chunks)} chunks")

            # 5) Post-process chunks (e.g. fallback for missing h1)
            chunks = self.post_process_chunks(chunks, document)
            logger.info(f"Post-processed {len(chunks)} chunks")

            # Collect all
            processed_chunks.extend(chunks)

        # 6) Validate
        if not processed_chunks:
            logger.warning("No chunks were generated from the input data")

        # 7) Return
        return processed_chunks

    @generic_error_handler
    def identify_sections(self, page_content: str, page_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Identify the sections and headers in the provided page content.
        Returns a list of { headers: dict, content: str } sections.
        """
        sections = []
        in_code_block = False
        code_fence = ""
        current_section = {"headers": {"h1": "", "h2": "", "h3": ""}, "content": ""}
        accumulated_content = ""

        lines = page_content.split("\n")
        for line in lines:
            stripped_line = line.strip()

            # Check for code block start/end
            code_block_start_match = self.code_block_start_pattern.match(stripped_line)
            if code_block_start_match:
                fence = code_block_start_match.group(1)
                if not in_code_block:
                    in_code_block = True
                    code_fence = fence
                elif stripped_line == code_fence:
                    in_code_block = False
                accumulated_content += line + "\n"
                continue
            elif in_code_block:
                accumulated_content += line + "\n"
                continue

            # If not in code block, check for headers
            header_match = self.h_pattern.match(stripped_line)
            if header_match:
                # Process accumulated content before this header
                if accumulated_content.strip():
                    current_section["content"] = accumulated_content.strip()
                    sections.append(current_section.copy())
                    accumulated_content = ""
                    # Reset current_section for the next section
                    current_section = {"headers": current_section["headers"].copy(), "content": ""}

                header_marker = header_match.group(1)
                header_level = len(header_marker)
                header_text = header_match.group(2).strip()
                cleaned_header_text = self.clean_header_text(
                    self.inline_code_pattern.sub(r"<code>\1</code>", header_text)
                )

                # Update headers after cleaning
                if header_level == 1:
                    current_section["headers"]["h1"] = cleaned_header_text
                    current_section["headers"]["h2"] = ""
                    current_section["headers"]["h3"] = ""
                elif header_level == 2:
                    current_section["headers"]["h2"] = cleaned_header_text
                    current_section["headers"]["h3"] = ""
                elif header_level == 3:
                    current_section["headers"]["h3"] = cleaned_header_text

            else:
                accumulated_content += line + "\n"

        # Process any remaining content
        if accumulated_content.strip():
            current_section["content"] = accumulated_content.strip()
            sections.append(current_section.copy())

        # Check for unclosed code block
        if in_code_block:
            logger.warning("Found unclosed code block - this might affect chunking quality")

        logger.debug(
            f"Section identification complete. Found {len(sections)} sections with "
            f"{sum(1 for s in sections if s['headers']['h1'])} h1 headers"
        )
        return sections

    @generic_error_handler
    def create_chunks(self, sections: list[dict[str, Any]], document: Document) -> list[Chunk]:
        """
        Converts the identified sections into final Chunk objects.

        Args:
            sections (list[dict[str, Any]]):
                Each section is a dictionary containing headers & content, e.g.:
                {
                  "headers": {"h1": "...", "h2": "...", "h3": "..."},
                  "content": "..."
                }
            document (Document):
                The source Document, from which we can retrieve metadata like source_id, etc.

        Returns:
            list[Chunk]: The final Chunk objects ready for embedding or storage.
        """
        page_chunks: list[dict[str, Any]] = []  # Add this line at start of method
        for section in sections:
            section_chunks = self.split_into_raw_chunks(section["content"], section["headers"])
            page_chunks.extend(section_chunks)

        # Adjust chunks for the entire page
        adjusted_chunks = self._adjust_chunks(page_chunks)

        intermediate_chunks: list[Chunk] = []
        for chunk in adjusted_chunks:
            new_chunk = Chunk(
                source_id=document.source_id,
                document_id=document.document_id,
                headers=chunk["headers"],
                text=chunk["content"],
                token_count=self._calculate_tokens(chunk["content"]),
                page_title=document.metadata.title or "Untitled",
                page_url=document.metadata.source_url,
            )
            intermediate_chunks.append(new_chunk)

        logger.debug(f"Created {len(intermediate_chunks)} final chunks")
        return intermediate_chunks

    @generic_error_handler
    def split_into_raw_chunks(self, content: str, headers: dict[str, str]) -> list[dict[str, Any]]:  # noqa: C901
        """
        Split the content into sections based on headers and code blocks.

        Args:
            content (str): The content to be split.
            headers (dict[str, str]): The headers associated with each content chunk.

        Returns:
            list[dict[str, Any]]: A list of dictionaries, each containing 'headers' and 'content'.

        Raises:
            ValidationError: If an unclosed code block is detected.
        """
        # TODO: refactor this method to reduce complexity
        # Current complexity is necessary for accurate content splitting
        chunks = []
        current_chunk = {"headers": headers.copy(), "content": ""}
        lines = content.split("\n")
        in_code_block = False
        code_fence = ""
        code_block_content = ""

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped_line = line.rstrip()

            # Check for code block start/end
            code_block_start_match = self.code_block_start_pattern.match(stripped_line)
            if code_block_start_match:
                fence = code_block_start_match.group(1)
                if not in_code_block:
                    in_code_block = True
                    code_fence = fence
                    code_block_content = line + "\n"
                elif stripped_line == code_fence:
                    code_block_content += line + "\n"
                    in_code_block = False

                    # Code block has ended; decide where to place it
                    code_block_tokens = self._calculate_tokens(code_block_content)
                    if code_block_tokens > 2 * self.max_tokens:
                        # Split the code block
                        split_code_blocks = self._split_code_block(code_block_content, code_fence)
                        for code_chunk in split_code_blocks:
                            code_chunk = code_chunk.strip()
                            if not code_chunk:
                                continue
                            # Wrap code chunk with code fence
                            code_chunk_content = f"{code_fence}\n{code_chunk}\n{code_fence}\n"
                            potential_chunk_content = current_chunk["content"] + code_chunk_content
                            token_count = self._calculate_tokens(potential_chunk_content)
                            if token_count <= 2 * self.max_tokens:
                                current_chunk["text"] = potential_chunk_content
                            else:
                                if current_chunk["content"].strip():
                                    chunks.append(current_chunk.copy())
                                current_chunk = {"headers": headers.copy(), "content": code_chunk_content}
                    else:
                        # Decide whether to add to current chunk or start a new one
                        potential_chunk_content = current_chunk["content"] + code_block_content
                        token_count = self._calculate_tokens(potential_chunk_content)
                        if token_count <= 2 * self.max_tokens:
                            current_chunk["content"] = potential_chunk_content
                        else:
                            if current_chunk["content"].strip():
                                chunks.append(current_chunk.copy())
                            current_chunk = {"headers": headers.copy(), "content": code_block_content}
                    code_block_content = ""
                else:
                    # Inside code block
                    code_block_content += line + "\n"
                i += 1
                continue

            elif in_code_block:
                code_block_content += line + "\n"
                i += 1
                continue

            # Handle regular lines
            line = self.inline_code_pattern.sub(r"<code>\1</code>", line)
            potential_chunk_content = current_chunk["content"] + line + "\n"
            token_count = self._calculate_tokens(potential_chunk_content)

            if token_count <= self.soft_token_limit:
                current_chunk["content"] = potential_chunk_content
            else:
                if current_chunk["content"].strip():
                    chunks.append(current_chunk.copy())
                # Check if the line itself exceeds 2 * max_tokens
                line_token_count = self._calculate_tokens(line + "\n")
                if line_token_count > 2 * self.max_tokens:
                    # Split the line into smaller chunks
                    split_lines = self._split_long_line(line)
                    for split_line in split_lines:
                        current_chunk = {"headers": headers.copy(), "content": split_line + "\n"}
                        chunks.append(current_chunk.copy())
                    current_chunk = {"headers": headers.copy(), "content": ""}
                else:
                    current_chunk = {"headers": headers.copy(), "content": line + "\n"}
            i += 1

        # After processing all lines, check for any unclosed code block
        if in_code_block:
            # Add remaining code block content to current_chunk
            current_chunk["content"] += code_block_content

        if current_chunk["content"].strip():
            chunks.append(current_chunk.copy())

        return chunks

    @generic_error_handler
    def _split_code_block(self, code_block_content: str, code_fence: str) -> list[str]:
        """
        Split a code block into smaller chunks based on token count.

        Args:
            code_block_content (str): The content of the code block to be split.
            code_fence (str): The code fence delimiter used to format the code block.

        Returns:
            list[str]: A list of code block chunks.

        Raises:
            None
        """
        lines = code_block_content.strip().split("\n")
        chunks = []
        current_chunk_lines = []
        for line in lines:
            current_chunk_lines.append(line)
            current_chunk = "\n".join(current_chunk_lines)
            token_count = self._calculate_tokens(f"{code_fence}\n{current_chunk}\n{code_fence}\n")
            if token_count >= 2 * self.max_tokens:
                # Attempt to find a logical split point
                split_index = len(current_chunk_lines) - 1
                for j in range(len(current_chunk_lines) - 1, -1, -1):
                    line_j = current_chunk_lines[j]
                    if (
                        line_j.strip() == ""
                        or line_j.strip().startswith("#")
                        or re.match(r"^\s*(def |class |\}|//|/\*|\*/)", line_j)
                    ):
                        split_index = j
                        break
                # Split at split_index
                chunk_content = "\n".join(current_chunk_lines[: split_index + 1])
                chunks.append(chunk_content.strip())
                # Start new chunk with remaining lines
                current_chunk_lines = current_chunk_lines[split_index + 1 :]
        # Add any remaining lines as the last chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if chunk_content.strip():
                chunks.append(chunk_content.strip())
        return chunks

    @generic_error_handler
    def _adjust_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Adjust chunks to be within the specified token limits.

        Adjusts the size of the given text chunks by merging small chunks and splitting large ones.

        Args:
            chunks: A list of dictionaries representing the chunks.

        Returns:
            A list of dictionaries representing the adjusted chunks.

        Raises:
            ValueError: If a chunk cannot be adjusted to meet the token requirements.
        """
        adjusted_chunks = []
        i = 0
        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = self._calculate_tokens(current_chunk["content"])
            # If the chunk is too small, try to merge with adjacent chunks
            if current_tokens < self.min_chunk_size:
                logger.debug(f"Found small chunk: {current_tokens} tokens")
                merged = False
                # Try merging with the next chunk
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    combined_content = current_chunk["content"] + next_chunk["content"]
                    combined_tokens = self._calculate_tokens(combined_content)
                    if combined_tokens <= 2 * self.max_tokens:
                        # Merge current and next chunk
                        merged_chunk = {
                            "headers": self._merge_headers(current_chunk["headers"], next_chunk["headers"]),
                            "content": combined_content,
                        }
                        # Replace next chunk with merged chunk
                        chunks[i + 1] = merged_chunk
                        i += 1  # Skip the current chunk, continue with merged chunk
                        merged = True
                if not merged and adjusted_chunks:
                    # Try merging with the previous chunk
                    prev_chunk = adjusted_chunks[-1]
                    combined_content = prev_chunk["content"] + current_chunk["content"]
                    combined_tokens = self._calculate_tokens(combined_content)
                    if combined_tokens <= 2 * self.max_tokens:
                        # Merge previous and current chunk
                        merged_chunk = {
                            "headers": self._merge_headers(prev_chunk["headers"], current_chunk["headers"]),
                            "content": combined_content,
                        }
                        adjusted_chunks[-1] = merged_chunk
                        i += 1
                        continue
                if not merged:
                    # Can't merge, add current chunk as is
                    adjusted_chunks.append(current_chunk)
                    i += 1
            else:
                # Chunk is of acceptable size, add to adjusted_chunks
                adjusted_chunks.append(current_chunk)
                i += 1

        # Now, split any chunks that exceed 2x max_tokens
        final_chunks = []
        for chunk in adjusted_chunks:
            token_count = self._calculate_tokens(chunk["content"])
            if token_count > 2 * self.max_tokens:
                split_chunks = self._split_large_chunk(chunk)
                final_chunks.extend(split_chunks)
            else:
                final_chunks.append(chunk)
        return final_chunks

    @generic_error_handler
    def _split_large_chunk(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Split a large text chunk into smaller chunks.

        Args:
            chunk (dict[str, Any]): A dictionary containing 'content' and 'headers' keys.
                                    'content' is the text to split, and 'headers' are additional metadata.

        Returns:
            list[dict[str, Any]]: A list of dictionaries where each dictionary contains a portion of the original
            content
                                  and a copy of the headers.

        Raises:
            KeyError: If 'content' or 'headers' keys are not found in the chunk dictionary.
            Any other exceptions raised by self._calculate_tokens method.
        """
        content = chunk["content"]
        headers = chunk["headers"]
        lines = content.split("\n")

        chunks = []
        current_chunk_content = ""
        for line in lines:
            potential_chunk_content = current_chunk_content + line + "\n"
            token_count = self._calculate_tokens(potential_chunk_content)
            if token_count <= 2 * self.max_tokens:
                current_chunk_content = potential_chunk_content
            else:
                if current_chunk_content.strip():
                    new_chunk = {"headers": headers.copy(), "content": current_chunk_content.strip()}
                    chunks.append(new_chunk)
                current_chunk_content = line + "\n"

        if current_chunk_content.strip():
            new_chunk = {"headers": headers.copy(), "content": current_chunk_content.strip()}
            chunks.append(new_chunk)

        return chunks

    @generic_error_handler
    def _merge_headers(self, headers1: dict[str, str], headers2: dict[str, str]) -> dict[str, str]:
        """
        Merge two headers dictionaries by levels.

        Args:
            headers1 (dict[str, str]): The first headers dictionary.
            headers2 (dict[str, str]): The second headers dictionary.

        Returns:
            dict[str, str]: The merged headers dictionary with levels "h1", "h2", and "h3".
        """
        merged = {}
        for level in ["h1", "h2", "h3"]:
            header1 = headers1.get(level, "").strip()
            header2 = headers2.get(level, "").strip()
            if header1:
                merged[level] = header1
            elif header2:
                merged[level] = header2
            else:
                merged[level] = ""
        return merged

    def _split_long_line(self, line: str) -> list[str]:
        """
        Split a long line of text into smaller chunks based on token limits.

        Args:
            line (str): The line of text to be split.

        Returns:
            list[str]: A list containing the smaller chunks of text.
        """
        tokens = self.tokenizer.encode(line)
        max_tokens_per_chunk = 2 * self.max_tokens
        chunks = []
        for i in range(0, len(tokens), max_tokens_per_chunk):
            chunk_tokens = tokens[i : i + max_tokens_per_chunk]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        return chunks

    def _get_last_n_tokens(self, text: str, n: int) -> str:
        """
        Get the last n tokens from the given text.

        Args:
            text (str): The text to tokenize.
            n (int): The number of tokens to retrieve from the end of the text.

        Returns:
            str: The decoded string of the last n tokens.

        Raises:
            ValueError: If n is greater than the number of tokens in the text.
        """
        tokens = self.tokenizer.encode(text)
        last_n_tokens = tokens[-n:]
        return self.tokenizer.decode(last_n_tokens)

    @generic_error_handler
    def _calculate_tokens(self, text: str) -> int:
        """
        Calculate the number of tokens in a given text.

        Args:
            text (str): The input text to be tokenized.

        Returns:
            int: The number of tokens in the input text.

        Raises:
            TokenizationError: If there is an error during tokenization.
        """
        token_count = len(self.tokenizer.encode(text))
        return token_count

    # Post-processing operations
    def post_process_chunks(self, chunk_list: list[Chunk], document: Document) -> list[Chunk]:
        """Post-process chunks to ensure consistency and add metadata."""
        page_title = document.metadata.title.strip() if document.metadata.title else "Untitled"

        # Ensure headers
        updated_chunks = [self.ensure_headers(chunk, page_title) for chunk in chunk_list]

        # Add overlap
        updated_chunks = self.add_overlap(updated_chunks)

        # Combine headers and text
        updated_chunks = self.combine_headers_and_text(updated_chunks)

        return updated_chunks

    def ensure_headers(self, chunk: Chunk, page_title: str) -> Chunk:
        if "h1" not in chunk.headers or not chunk.headers["h1"]:
            chunk.headers["h1"] = page_title
        return chunk

    @generic_error_handler
    def add_overlap(
        self, chunks: list[Chunk], min_overlap_tokens: int = 50, max_overlap_tokens: int = 100
    ) -> list[Chunk]:
        """
        Add overlap to chunks of text based on specified token limits.

        Args:
            chunks (list[Chunk]): List of text chunks with metadata.
            min_overlap_tokens (int): Minimum number of tokens for the overlap.
            max_overlap_tokens (int): Maximum number of tokens for the overlap.

        Returns:
            list[Chunk]: List of chunks with overlap added.

        Raises:
            ValidationError: If adding overlap exceeds the maximum allowed tokens.
        """
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            prev_chunk_text = prev_chunk.text

            # Calculate overlap tokens
            overlap_token_count = max(
                int(self._calculate_tokens(prev_chunk_text) * self.overlap_percentage), min_overlap_tokens
            )
            overlap_token_count = min(overlap_token_count, max_overlap_tokens)

            # Ensure that adding overlap does not exceed max_tokens
            current_chunk_token_count = curr_chunk.token_count
            available_space = self.max_tokens - current_chunk_token_count
            allowed_overlap_tokens = min(overlap_token_count, available_space)
            if allowed_overlap_tokens <= 0:
                continue

            overlap_text = self._get_last_n_tokens(prev_chunk_text, allowed_overlap_tokens)
            additional_tokens = self._calculate_tokens(overlap_text)
            curr_chunk.text = overlap_text + curr_chunk.text
            curr_chunk.token_count += additional_tokens

        return chunks

    def combine_headers_and_text(self, chunk_list: list[Chunk]) -> list[Chunk]:
        for chunk in chunk_list:
            chunk.content = f"Headers: {chunk.headers}\n\n Content: {chunk.text}"
        return chunk_list

    def save_chunks(self, chunks: list[Chunk], output_path: str = "chunks.json") -> None:
        """
        Save chunks to a JSON file for inspection.

        Args:
            chunks: List of chunks to save
            output_path: Where to save the chunks (defaults to chunks.json in current directory)
        """
        import json
        from datetime import datetime

        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "num_chunks": len(chunks),
                "settings": {
                    "max_tokens": self.max_tokens,
                    "soft_token_limit": self.soft_token_limit,
                    "min_chunk_size": self.min_chunk_size,
                    "overlap_percentage": self.overlap_percentage,
                },
            },
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(chunks)} chunks to {output_path}")
        logger.info(
            f"Saved chunks. Stats: "
            f"Min tokens: {min(c.token_count for c in chunks)}, "
            f"Max tokens: {max(c.token_count for c in chunks)}, "
            f"Avg tokens: {sum(c.token_count for c in chunks)/len(chunks):.1f}"
        )

    # Validation operations
    # Calculate key chunking metrics


async def get_documents(source_id: UUID) -> list[Document]:
    """Get documents for a specific source from Supabase."""
    # Setup
    supabase_manager = await SupabaseManager.create_async()
    repository = DataRepository(supabase_manager=supabase_manager)
    data_service = DataService(repository=repository)

    # Get documents (limit to 15)
    documents = await data_service.get_documents_by_source(source_id=source_id)

    return documents


async def test_chunker(source_id: str) -> None:
    """Test the chunker with documents from a specific source."""
    try:
        # Convert string to UUID
        source_uuid = UUID(source_id)

        # Get documents
        documents = await get_documents(source_uuid)
        logger.info(f"Retrieved {len(documents)} documents")

        # Initialize chunker
        chunker = MarkdownChunker()

        # Process documents
        chunks = chunker.process_documents(documents)
        logger.info(f"Generated {len(chunks)} chunks")

        # Save chunks for inspection
        chunker.save_chunks(chunks, "test_chunks.json")

        # Print some stats
        total_tokens = sum(chunk.token_count for chunk in chunks)
        avg_tokens = total_tokens / len(chunks) if chunks else 0

        print("\nChunking Results:")
        print(f"Total documents processed: {len(documents)}")
        print(f"Total chunks generated: {len(chunks)}")
        print(f"Average tokens per chunk: {avg_tokens:.1f}")
        print("Results saved to: test_chunks.json")

    except Exception as e:
        logger.error(f"Error testing chunker: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio

    configure_logging(debug=True)

    SOURCE_ID = "37a806c4-6508-4bec-8e66-e6b142195838"

    # Run the test
    asyncio.run(test_chunker(SOURCE_ID))
