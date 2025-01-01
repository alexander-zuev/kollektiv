import json
import os
import re
import uuid
from typing import Any

import tiktoken

from src.infra.decorators import generic_error_handler
from src.infra.logger import get_logger
from src.models.content_models import Chunk, Document

logger = get_logger()


class PreProcessor:
    """Pre-processes data before chunking."""

    pass


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

    def batch_documents(self, documents: list[Document]) -> list[list[Document]]:
        """Batch documents into smaller chunks."""
        return [documents[i : i + self.document_batch_size] for i in range(0, len(documents), self.document_batch_size)]

    def batch_chunks(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        """Batch chunks into smaller chunks."""
        return [chunks[i : i + self.chunk_batch_size] for i in range(0, len(chunks), self.chunk_batch_size)]

    @generic_error_handler
    def process_documents(self, documents: list[Document]) -> list[Chunk]:
        """
        Process documents and generate chunks.

        Args:
            documents (list[Document]): The documents to be processed.

        Returns:
            list[Chunk]: A list of processed chunks.

        Raises:
            ValueError: If there is an issue with the page content processing.
        """
        all_chunks = []
        # Access the nested data structure correctly
        pages = json_input.get("data", {}).get("data", [])

        for page in pages:
            page_content = page.get("markdown", "")
            page_metadata = page.get("metadata", {})

            # Skip empty content
            if not page_content.strip():
                logger.warning(f"Skipping empty page content for URL: {page_metadata.get('sourceURL', 'unknown')}")
                continue

            page_content = self.remove_boilerplate(page_content)
            page_content = self.remove_images(page_content)

            sections = self.identify_sections(page_content, page_metadata)
            chunks = self.create_chunks(sections, page_metadata)

            # Post-processing: Ensure headers fallback to page title if missing
            page_title = page_metadata.get("title", "Untitled")
            for chunk in chunks:
                if not chunk["data"]["headers"].get("h1"):
                    chunk["data"]["headers"]["h1"] = page_title
                    # Increment total headings for H1 when setting from page title
                    if page_title.strip() not in self.validator.total_headings["h1"]:
                        self.validator.increment_total_headings("h1", page_title)

            all_chunks.extend(chunks)

        # After processing all pages, perform validation
        if not all_chunks:
            logger.warning("No chunks were generated from the input data")

        self.validator.validate(all_chunks)
        return all_chunks

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

    @generic_error_handler
    def identify_sections(self, page_content: str, page_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Identify the sections and headers in the provided page content.

        Args:
            page_content (str): The content of the page to be analyzed.
            page_metadata (dict[str, Any]): Metadata of the page provided as a dictionary.

        Returns:
            list[dict[str, Any]]: A list of sections, each represented as a dictionary with headers and content.

        Raises:
            ValueError: If an unclosed code block is detected.
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

                # Update validator counts
                self.validator.increment_total_headings(f"h{header_level}", cleaned_header_text)
            else:
                accumulated_content += line + "\n"

        # Process any remaining content
        if accumulated_content.strip():
            current_section["content"] = accumulated_content.strip()
            sections.append(current_section.copy())

        # Check for unclosed code block
        if in_code_block:
            self.validator.add_validation_error("Unclosed code block detected.")

        return sections

    @generic_error_handler
    def create_chunks(self, sections: list[dict[str, Any]], page_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Create chunks from sections and adjust them according to page metadata.

        Args:
            sections (list[dict[str, Any]]): List of sections, where each section is a dictionary with "content" and
            "headers".
            page_metadata (dict[str, Any]): Metadata related to the page, used to enrich chunk metadata.

        Returns:
            list[dict[str, Any]]: A list of adjusted and enriched chunks with ids, metadata, and data.

        Raises:
            CustomException: If validation or adjustment fails during the chunk creation process.
        """
        page_chunks = []
        for section in sections:
            section_chunks = self._split_section(section["content"], section["headers"])
            page_chunks.extend(section_chunks)

        # Adjust chunks for the entire page
        adjusted_chunks = self._adjust_chunks(page_chunks)

        final_chunks = []
        for chunk in adjusted_chunks:
            chunk_id = str(self._generate_chunk_id())
            token_count = self._calculate_tokens(chunk["content"])
            self.validator.add_chunk(token_count)
            metadata = self._create_metadata(page_metadata, token_count)
            new_chunk = {
                "chunk_id": chunk_id,
                "metadata": metadata,
                "data": {"headers": chunk["headers"], "text": chunk["content"]},
            }
            final_chunks.append(new_chunk)

        # After chunks are created, update headings preserved
        for chunk in final_chunks:
            headers = chunk["data"]["headers"]
            for level in ["h1", "h2", "h3"]:
                heading_text = headers.get(level)
                if heading_text:
                    self.validator.add_preserved_heading(level, heading_text)

        # Add overlap as the final step
        self._add_overlap(final_chunks)
        return final_chunks

    @generic_error_handler
    def _split_section(self, content: str, headers: dict[str, str]) -> list[dict[str, Any]]:  # noqa: C901
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
                                current_chunk["content"] = potential_chunk_content
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
            self.validator.add_validation_error("Unclosed code block detected.")
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
            chunks: A list of dictionaries, where each dictionary contains headers and content.

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

    @generic_error_handler
    def _add_overlap(
        self, chunks: list[dict[str, Any]], min_overlap_tokens: int = 50, max_overlap_tokens: int = 100
    ) -> None:
        """
        Add overlap to chunks of text based on specified token limits.

        Args:
            chunks (list[dict[str, Any]]): List of text chunks with metadata.
            min_overlap_tokens (int): Minimum number of tokens for the overlap.
            max_overlap_tokens (int): Maximum number of tokens for the overlap.

        Returns:
            None.

        Raises:
            ValidationError: If adding overlap exceeds the maximum allowed tokens.
        """
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            prev_chunk_text = prev_chunk["data"]["text"]

            # Calculate overlap tokens
            overlap_token_count = max(
                int(self._calculate_tokens(prev_chunk_text) * self.overlap_percentage), min_overlap_tokens
            )
            overlap_token_count = min(overlap_token_count, max_overlap_tokens)

            # Ensure that adding overlap does not exceed max_tokens
            current_chunk_token_count = curr_chunk["metadata"]["token_count"]
            available_space = self.max_tokens - current_chunk_token_count
            allowed_overlap_tokens = min(overlap_token_count, available_space)
            if allowed_overlap_tokens <= 0:
                # Cannot add overlap without exceeding max_tokens
                self.validator.add_validation_error(
                    f"Cannot add overlap to chunk {curr_chunk['chunk_id']} without exceeding max_tokens"
                )
                continue

            overlap_text = self._get_last_n_tokens(prev_chunk_text, allowed_overlap_tokens)
            additional_tokens = self._calculate_tokens(overlap_text)
            curr_chunk["data"]["text"] = overlap_text + curr_chunk["data"]["text"]
            curr_chunk["metadata"]["token_count"] += additional_tokens

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
    def save_chunks(self, chunks: list[dict[str, Any]]) -> str:
        """
        Save the given chunks to a JSON file.

        Args:
            chunks (list of dict): A list of dictionaries containing chunk data.

        Raises:
            Exception: If an error occurs while saving the chunks to the file.
        """
        input_name = os.path.splitext(self.input_filename)[0]  # Remove the extension
        output_filename = f"{input_name}-chunked.json"
        output_filepath = os.path.join(self.output_dir, output_filename)
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)
        logger.info(f"Chunks saved to {output_filepath}")

        return output_filename

    @generic_error_handler
    def _generate_chunk_id(self) -> uuid.UUID:
        """
        Generate a new UUID for chunk identification.

        Returns:
            uuid.UUID: A new unique identifier for the chunk.

        """
        return uuid.uuid4()

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

    @generic_error_handler
    def _create_metadata(self, page_metadata: dict[str, Any], token_count: int) -> dict[str, Any]:
        """
        Create metadata dictionary for a page.

        Args:
            page_metadata (dict[str, Any]): Metadata extracted from a page.
            token_count (int): Number of tokens in the page content.

        Returns:
            dict[str, Any]: A dictionary containing the token count, source URL, and page title.

        Raises:
            None
        """
        metadata = {
            "token_count": token_count,
            "source_url": page_metadata.get("sourceURL", ""),
            "page_title": page_metadata.get("title", ""),
        }
        return metadata
