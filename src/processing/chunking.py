import json
import os
import re
import statistics
import uuid
from typing import Any

import tiktoken

from src.utils.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.utils.decorators import error_handler
from src.utils.logger import setup_logger

logger = setup_logger("chunker", "chunking.log")


class MarkdownChunker:
    def __init__(
        self,
        input_filename: str,
        output_dir: str = PROCESSED_DATA_DIR,
        max_tokens: int = 1000,
        soft_token_limit: int = 800,
        min_chunk_size: int = 100,
        overlap_percentage: float = 0.05,
    ):
        self.output_dir = output_dir
        self.logger = logger
        self.input_filename = input_filename
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = max_tokens  # Hard limit
        self.soft_token_limit = soft_token_limit  # Soft limit
        self.min_chunk_size = min_chunk_size  # Minimum chunk size in tokens
        self.overlap_percentage = overlap_percentage  # 5% overlap
        # Initialize the validator
        self.validator = MarkdownChunkValidator(
            logger=self.logger,
            min_chunk_size=self.min_chunk_size,
            max_tokens=self.max_tokens,
            output_dir=self.output_dir,
            input_filename=self.input_filename,
        )

        # Precompile regex patterns for performance
        self.boilerplate_patterns = [
            r"\[Anthropic home page.*\]\(/.*\)",  # Matches the home page link with images
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

    @error_handler(logger)
    def load_data(self) -> dict[str, Any]:
        """Loads markdown from JSON and prepares for chunking"""
        input_filepath = os.path.join(RAW_DATA_DIR, self.input_filename)

        try:
            with open(input_filepath, encoding="utf-8") as f:
                doc = json.load(f)
            self.logger.info(f"{self.input_filename} loaded")
            return doc
        except FileNotFoundError:
            self.logger.error(f"File not found: {input_filepath}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in file: {input_filepath}")
            raise

    @error_handler(logger)
    def process_pages(self, json_input: dict[str, Any]) -> list[dict[str, Any]]:
        """Iterates through each page in the loaded data"""
        all_chunks = []
        for _index, page in enumerate(json_input["data"]):
            page_content = page["markdown"]
            page_content = self.remove_boilerplate(page_content)
            page_metadata = page["metadata"]

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
        self.validator.validate(all_chunks)
        return all_chunks

    @error_handler(logger)
    def remove_boilerplate(self, content: str) -> str:
        """Removes navigation and boilerplate content from markdown."""
        # Use precompiled regex
        cleaned_content = self.boilerplate_regex.sub("", content)
        # Remove any extra newlines left after removing boilerplate
        cleaned_content = re.sub(r"\n{2,}", "\n\n", cleaned_content)
        return cleaned_content.strip()

    @error_handler(logger)
    def clean_header_text(self, header_text: str) -> str:
        """Cleans unwanted markdown elements and artifacts from header text."""
        # Remove zero-width spaces
        cleaned_text = header_text.replace("\u200b", "")
        # Remove markdown links but keep the link text
        cleaned_text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned_text)
        # Remove images in headers
        cleaned_text = re.sub(r"!\[.*?\]\(.*?\)", "", cleaned_text)
        cleaned_text = cleaned_text.strip()
        # Ensure shell commands are not mistaken as headers
        if cleaned_text.startswith("!/") or cleaned_text.startswith("#!"):
            cleaned_text = ""  # Empty out any shell commands mistaken as headers
        return cleaned_text

    @error_handler(logger)
    def identify_sections(self, page_content: str, page_metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Identifies sections in the page content based on headers and preserves markdown structures."""
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

    @error_handler(logger)
    def create_chunks(self, sections: list[dict[str, Any]], page_metadata: dict[str, Any]) -> list[dict[str, Any]]:
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

    @error_handler(logger)
    def _split_section(self, content: str, headers: dict[str, str]) -> list[dict[str, Any]]:  # noqa: C901
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

    @error_handler(logger)
    def _split_code_block(self, code_block_content: str, code_fence: str) -> list[str]:
        """Splits a code block into smaller chunks without breaking code syntax."""
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

    @error_handler(logger)
    def _adjust_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Adjust chunks to meet min and max token constraints by merging or splitting."""
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

    @error_handler(logger)
    def _split_large_chunk(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        """Splits a chunk that exceeds 2x max_tokens into smaller chunks."""
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

    @error_handler(logger)
    def _merge_headers(self, headers1: dict[str, str], headers2: dict[str, str]) -> dict[str, str]:
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

    @error_handler(logger)
    def _add_overlap(
        self, chunks: list[dict[str, Any]], min_overlap_tokens: int = 50, max_overlap_tokens: int = 100
    ) -> None:
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
        """Splits a long line into smaller chunks not exceeding 2 * max_tokens."""
        tokens = self.tokenizer.encode(line)
        max_tokens_per_chunk = 2 * self.max_tokens
        chunks = []
        for i in range(0, len(tokens), max_tokens_per_chunk):
            chunk_tokens = tokens[i : i + max_tokens_per_chunk]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        return chunks

    def _get_last_n_tokens(self, text: str, n: int) -> str:
        tokens = self.tokenizer.encode(text)
        last_n_tokens = tokens[-n:]
        return self.tokenizer.decode(last_n_tokens)

    @error_handler(logger)
    def save_chunks(self, chunks: list[dict[str, Any]]):
        """Saves chunks to output dir"""
        input_name = os.path.splitext(self.input_filename)[0]  # Remove the extension
        output_filename = f"{input_name}-chunked.json"
        output_filepath = os.path.join(self.output_dir, output_filename)
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)
        self.logger.info(f"Chunks saved to {output_filepath}")

    @error_handler(logger)
    def _generate_chunk_id(self) -> uuid.UUID:
        """Generates chunk's uuidv4"""
        return uuid.uuid4()

    @error_handler(logger)
    def _calculate_tokens(self, text: str) -> int:
        """Calculates the number of tokens in a given text using tiktoken"""
        token_count = len(self.tokenizer.encode(text))
        return token_count

    @error_handler(logger)
    def _create_metadata(self, page_metadata: dict[str, Any], token_count: int) -> dict[str, Any]:
        """Creates metadata dictionary for a chunk"""
        metadata = {
            "token_count": token_count,
            "source_url": page_metadata.get("sourceURL", ""),
            "page_title": page_metadata.get("title", ""),
        }
        return metadata


class MarkdownChunkValidator:
    def __init__(self, logger, min_chunk_size, max_tokens, output_dir, input_filename):
        self.logger = logger
        self.min_chunk_size = min_chunk_size
        self.max_tokens = max_tokens
        self.output_dir = output_dir
        self.input_filename = input_filename
        # Validation-related attributes
        self.validation_errors = []
        self.total_chunks = 0
        self.total_tokens = 0
        self.chunk_token_counts = []
        self.headings_preserved = {"h1": set(), "h2": set(), "h3": set()}
        self.total_headings = {"h1": set(), "h2": set(), "h3": set()}
        self.incorrect_counts = {"too_small": 0, "too_large": 0}
        self.duplicates_removed = 0  # New attribute to track duplicates removed

    def increment_total_headings(self, level, heading_text):
        self.total_headings[level].add(heading_text.strip())

    def add_preserved_heading(self, level, heading_text):
        self.headings_preserved[level].add(heading_text.strip())

    def add_chunk(self, token_count):
        self.total_chunks += 1
        self.total_tokens += token_count
        self.chunk_token_counts.append(token_count)

    def add_validation_error(self, error_message):
        self.validation_errors.append(error_message)

    def validate(self, chunks):
        self.validate_duplicates(chunks)
        self.find_incorrect_chunks(chunks)
        self.log_summary()

    def validate_duplicates(self, chunks: list[dict[str, Any]]) -> None:
        """Removes duplicate chunks and updates counts."""
        unique_chunks = {}
        cleaned_chunks = []
        for chunk in chunks:
            text = chunk["data"]["text"]
            if text in unique_chunks:
                self.duplicates_removed += 1
                # Log the duplicate chunk removal
                self.logger.warning(f"Duplicate chunk found and removed: {chunk['chunk_id']}")
                continue
            else:
                unique_chunks[text] = True
                cleaned_chunks.append(chunk)

        # Update the chunks list to the cleaned_chunks without duplicates
        chunks.clear()
        chunks.extend(cleaned_chunks)
        self.total_chunks = len(chunks)

    def log_summary(self):
        """Logs a concise summary of the chunking process"""
        # Total chunks
        self.logger.info(f"Total chunks created: {self.total_chunks}")

        # Duplicate chunks removed
        self.logger.info(f"Duplicate chunks removed: {self.duplicates_removed}")

        # Chunk statistics
        if self.chunk_token_counts:
            median_tokens = statistics.median(self.chunk_token_counts)
            min_tokens = min(self.chunk_token_counts)
            max_tokens = max(self.chunk_token_counts)
            p25 = statistics.quantiles(self.chunk_token_counts, n=4)[0]
            p75 = statistics.quantiles(self.chunk_token_counts, n=4)[2]
            self.logger.info(
                f"Chunk token statistics - Median: {median_tokens}, Min: {min_tokens}, "
                f"Max: {max_tokens}, 25th percentile: {p25}, 75th percentile: {p75}"
            )
        else:
            self.logger.warning("No chunks to calculate statistics.")

        # Headers summary
        headers_info = []
        for level in ["h1", "h2", "h3"]:
            total = len(self.total_headings.get(level, set()))
            preserved = len(self.headings_preserved.get(level, set()))
            percentage = (preserved / total * 100) if total > 0 else 0
            headers_info.append(f"{level.upper()} preserved: {preserved}/{total} ({percentage:.2f}%)")
        self.logger.info("Headers summary - " + ", ".join(headers_info))

        # Validation errors summary
        if self.validation_errors:
            error_counts = {}
            for error in self.validation_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
            total_errors = sum(error_counts.values())
            self.logger.warning(f"Validation issues encountered: {total_errors} issues found.")
            for error, count in error_counts.items():
                self.logger.warning(f"Validation error: {error!r} occurred {count} times.")
        else:
            self.logger.info("No validation issues encountered.")

        # Incorrect chunks summary
        incorrect_chunks_info = (
            f"Incorrect chunks - Too small: {self.incorrect_counts.get('too_small', 0)}, "
            f"Too large: {self.incorrect_counts.get('too_large', 0)}"
        )
        self.logger.info(incorrect_chunks_info)

    def find_incorrect_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Finds chunks below min_chunk_size or above 2x max_tokens and saves to JSON."""
        incorrect = {
            "too_small": [
                {
                    "id": c["chunk_id"],
                    "size": c["metadata"]["token_count"],
                    "headers": c["data"]["headers"],
                    "text": c["data"]["text"],
                }
                for c in chunks
                if c["metadata"]["token_count"] < self.min_chunk_size
            ],
            "too_large": [
                {
                    "id": c["chunk_id"],
                    "size": c["metadata"]["token_count"],
                    "headers": c["data"]["headers"],
                    "text": c["data"]["text"],
                }
                for c in chunks
                if c["metadata"]["token_count"] > 2 * self.max_tokens
            ],
        }

        # Store counts for logging summary
        self.incorrect_counts = {"too_small": len(incorrect["too_small"]), "too_large": len(incorrect["too_large"])}

        if any(incorrect.values()):
            base_name = os.path.splitext(self.input_filename)[0]
            output_filename = f"{base_name}-incorrect-chunks.json"
            output_filepath = os.path.join(self.output_dir, output_filename)

            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(incorrect, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Incorrect chunks saved to {output_filepath}")
        else:
            self.logger.info("No incorrect chunks found.")


# Test usage
def main():
    markdown_chunker = MarkdownChunker(input_filename="supabase_com_docs_guides_auth_20240916_235100.json")
    result = markdown_chunker.load_data()
    chunks = markdown_chunker.process_pages(result)
    markdown_chunker.save_chunks(chunks)


if __name__ == "__main__":
    main()
