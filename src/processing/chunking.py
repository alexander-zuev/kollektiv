import uuid
import json
import os
import re
import statistics
from typing import List, Dict, Any

import tiktoken

from src.utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from src.utils.logger import setup_logger
from src.utils.decorators import error_handler

logger = setup_logger('chunker', 'chunking.log')

class MarkdownChunker:
    def __init__(self,
                 input_filename: str,
                 output_dir: str = PROCESSED_DATA_DIR,
                 max_tokens: int = 1000,
                 soft_token_limit: int = 800,
                 min_chunk_size: int = 100,
                 overlap_percentage: float = 0.05):
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
            input_filename=self.input_filename
        )

    @error_handler(logger)
    def load_data(self) -> Dict[str, Any]:
        """Loads markdown from JSON and prepares for chunking"""
        input_filepath = os.path.join(RAW_DATA_DIR, self.input_filename)

        try:
            with open(input_filepath, 'r', encoding='utf-8') as f:
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
    def process_pages(self, json_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Iterates through each page in the loaded data"""
        all_chunks = []
        original_content = ''
        for index, page in enumerate(json_input['data']):
            page_content = page['markdown']
            original_content += page_content
            page_metadata = page['metadata']

            sections = self.identify_sections(page_content, page_metadata)
            chunks = self.create_chunks(sections, page_metadata)

            # Post-processing: H1 fallback
            page_title = page_metadata.get('title', 'Untitled')
            for chunk in chunks:
                if not chunk['data']['headers'].get('h1'):
                    chunk['data']['headers']['h1'] = page_title

            all_chunks.extend(chunks)

        # Calculate tokens in original content
        original_content_tokens = self._calculate_tokens(original_content)
        self.validator.set_original_content_tokens(original_content_tokens)

        # After processing all pages, perform validation
        self.validator.validate(all_chunks, original_content)
        return all_chunks

    @error_handler(logger)
    def identify_sections(self, page_content: str, page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identifies sections in the page content based on headers"""
        sections = []

        # Patterns for headers
        h_pattern = re.compile(r'^(#{1,6})\s*(.*)$', re.MULTILINE)

        # Find all headers
        headers = [
            (m.start(), m.end(), m.group(1), m.group(2).strip())
            for m in h_pattern.finditer(page_content)
        ]
        headers.sort()

        # Count total headings in original content
        for _, _, header_marker, header_text in headers:
            header_level = len(header_marker)
            if header_level == 1:
                self.validator.increment_total_headings('h1')
            elif header_level == 2:
                self.validator.increment_total_headings('h2')

        # If no headers found, treat the entire content as one section
        if not headers:
            sections.append({
                "headers": {
                    "h1": page_metadata.get('title', 'Untitled')
                },
                "content": page_content.strip()
            })
            # Track the h1 heading
            self.validator.add_preserved_heading('h1', page_metadata.get('title', 'Untitled'))
            self.validator.increment_total_headings('h1')  # Since we are using the page title as h1
            return sections

        # Process headers and content
        last_index = 0
        current_section = {
            "headers": {
                "h1": "",
                "h2": "",
                "h3": ""
            },
            "content": ""
        }

        for idx, (start, end, header_marker, header_text) in enumerate(headers):
            # Clean header text to remove markdown artifacts
            header_text = re.sub(r'!\[.*?\]\(.*?\)', '', header_text)  # Remove images
            header_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', header_text)  # Remove links but keep text
            header_text = header_text.strip()

            header_level = len(header_marker)
            header = header_text

            # Extract content before this header
            content = page_content[last_index:start].strip()
            if content:
                current_section['content'] = content
                sections.append(current_section.copy())
                current_section['content'] = ""

            # Update headers based on header level
            if header_level == 1:
                current_section['headers']['h1'] = header
                current_section['headers']['h2'] = ""
                current_section['headers']['h3'] = ""
                # Track h1 headings
                self.validator.add_preserved_heading('h1', header)
            elif header_level == 2:
                current_section['headers']['h2'] = header
                current_section['headers']['h3'] = ""
                # Track h2 headings
                self.validator.add_preserved_heading('h2', header)
            elif header_level == 3:
                current_section['headers']['h3'] = header

            last_index = end

        # Add remaining content after the last header
        content = page_content[last_index:].strip()
        if content:
            current_section['content'] = content
            sections.append(current_section.copy())

        return sections

    @error_handler(logger)
    def create_chunks(self, sections: List[Dict[str, Any]], page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        page_chunks = []
        for section in sections:
            section_chunks = self._split_section(section['content'], section['headers'])
            page_chunks.extend(section_chunks)

        # Adjust chunks for the entire page
        adjusted_chunks = self._adjust_chunks(page_chunks)

        final_chunks = []
        for chunk in adjusted_chunks:
            chunk_id = str(self._generate_chunk_id())
            token_count = self._calculate_tokens(chunk['content'])
            self.validator.add_chunk(token_count)
            metadata = self._create_metadata(page_metadata, token_count)
            new_chunk = {
                'chunk_id': chunk_id,
                'metadata': metadata,
                'data': {
                    'headers': chunk['headers'],
                    'text': chunk['content']
                }
            }
            final_chunks.append(new_chunk)

        # Add overlap as the final step
        self._add_overlap(final_chunks)
        return final_chunks

    @error_handler(logger)
    def _split_section(self, content: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        chunks = []
        current_chunk = {'headers': headers.copy(), 'content': ''}
        lines = content.split('\n')
        in_code_block = False
        code_fence = ''

        for line in lines:
            stripped_line = line.strip()

            # Check for code block start/end
            if stripped_line.startswith('```') or stripped_line.startswith('~~~'):
                if not in_code_block:
                    in_code_block = True
                    code_fence = stripped_line[:3]
                elif stripped_line.startswith(code_fence):
                    in_code_block = False
                    code_fence = ''

            # Handle inline code
            if not in_code_block:
                line = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', line)

            potential_chunk_content = current_chunk['content'] + line + '\n'
            token_count = self._calculate_tokens(potential_chunk_content)

            if token_count <= self.soft_token_limit or in_code_block:
                current_chunk['content'] += line + '\n'
            else:
                if in_code_block:
                    if token_count <= self.max_tokens:
                        current_chunk['content'] += line + '\n'
                    else:
                        self.validator.add_validation_error(
                            f"Code block exceeds hard token limit in headers {headers}"
                        )
                else:
                    if current_chunk['content'].strip():
                        chunks.append(current_chunk.copy())
                    current_chunk = {'headers': headers.copy(), 'content': line + '\n'}

        if current_chunk['content'].strip():
            chunks.append(current_chunk.copy())

        return chunks

    @error_handler(logger)
    def _adjust_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        adjusted_chunks = []
        current_chunk = None

        for chunk in chunks:
            if current_chunk is None:
                current_chunk = chunk
            else:
                combined_content = current_chunk['content'] + chunk['content']
                combined_tokens = self._calculate_tokens(combined_content)

                if combined_tokens <= self.soft_token_limit:
                    # Merge chunks
                    current_chunk['content'] = combined_content
                    current_chunk['headers'] = self._merge_headers(current_chunk['headers'], chunk['headers'])
                elif combined_tokens <= self.max_tokens and (
                        self._calculate_tokens(current_chunk['content']) < self.min_chunk_size or
                        self._calculate_tokens(chunk['content']) < self.min_chunk_size
                ):
                    # Force merge if one of the chunks is too small, even if it exceeds soft limit
                    current_chunk['content'] = combined_content
                    current_chunk['headers'] = self._merge_headers(current_chunk['headers'], chunk['headers'])
                else:
                    # Can't merge, add current_chunk to adjusted_chunks and start a new one
                    if self._calculate_tokens(current_chunk['content']) > self.max_tokens:
                        # Split large chunk
                        split_chunks = self._split_large_chunk(current_chunk)
                        adjusted_chunks.extend(split_chunks)
                    else:
                        adjusted_chunks.append(current_chunk)
                    current_chunk = chunk

        if current_chunk:
            if self._calculate_tokens(current_chunk['content']) > self.max_tokens:
                # Split last large chunk if necessary
                split_chunks = self._split_large_chunk(current_chunk)
                adjusted_chunks.extend(split_chunks)
            else:
                adjusted_chunks.append(current_chunk)

        return adjusted_chunks

    @error_handler(logger)
    def _merge_headers(self, headers1: Dict[str, str], headers2: Dict[str, str]) -> Dict[str, str]:
        merged = headers1.copy()
        for level in ['h1', 'h2', 'h3']:
            if headers2.get(level) and headers2[level] != headers1.get(level):
                merged[level] = headers2[level]
        return merged

    def _split_large_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = chunk['content']
        headers = chunk['headers']
        lines = content.split('\n')
        split_chunks = []
        current_chunk = {'headers': headers.copy(), 'content': ''}

        for line in lines:
            potential_content = current_chunk['content'] + line + '\n'
            if self._calculate_tokens(potential_content) <= self.soft_token_limit:
                current_chunk['content'] = potential_content
            else:
                if current_chunk['content']:
                    split_chunks.append(current_chunk)
                current_chunk = {'headers': headers.copy(), 'content': line + '\n'}

        if current_chunk['content']:
            split_chunks.append(current_chunk)

        return split_chunks

    @error_handler(logger)
    def _add_overlap(self,
                     chunks: List[Dict[str, Any]],
                     min_overlap_tokens: int = 50,
                     max_overlap_tokens: int = 100) -> None:

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            prev_chunk_text = prev_chunk['data']['text']

            # Calculate overlap tokens
            overlap_token_count = max(
                int(self._calculate_tokens(prev_chunk_text) * self.overlap_percentage),
                min_overlap_tokens
            )
            overlap_token_count = min(overlap_token_count, max_overlap_tokens)

            overlap_text = self._get_last_n_tokens(prev_chunk_text, overlap_token_count)

            curr_chunk['data']['overlap_text'] = {
                'previous_chunk_id': prev_chunk['chunk_id'],
                'text': overlap_text
            }

    def _get_last_n_tokens(self, text: str, n: int) -> str:
        tokens = self.tokenizer.encode(text)
        last_n_tokens = tokens[-n:]
        return self.tokenizer.decode(last_n_tokens)

    @error_handler(logger)
    def validate_all_chunks(self, chunks: List[Dict[str, Any]], original_content: str):
        """Performs overall validation of chunks"""
        # Check if total tokens in chunks match the original content
        combined_chunk_content = ''.join(chunk['data']['text'] for chunk in chunks)
        if combined_chunk_content.strip() != original_content.strip():
            # Determine if content is missing
            original_length = len(original_content.strip())
            combined_length = len(combined_chunk_content.strip())
            length_difference = original_length - combined_length
            percentage_difference = (abs(length_difference) / original_length) * 100

            if length_difference > 0:
                self.content_missing = True
                self.validation_errors.append(
                    f"Content missing from chunks. Missing {length_difference} "
                    f"characters ({percentage_difference:.2f}%)."
                )
                # No need to log here; summary will handle it
            else:
                self.content_missing = False
                # Having extra content may be acceptable
                # No need to log here; summary will handle it

        # Check for duplicates and remove them carefully
        chunk_texts = {}
        duplicates_found = False
        cleaned_chunks = []
        for chunk in chunks:
            text = chunk['data']['text']
            if text in chunk_texts:
                duplicates_found = True
                # Duplicates are fixed here; no need to report them
                continue
            else:
                chunk_texts[text] = True
                cleaned_chunks.append(chunk)

        if duplicates_found:
            # Update the chunks list to the cleaned_chunks without duplicates
            chunks.clear()
            chunks.extend(cleaned_chunks)
            self.total_chunks = len(chunks)

    @error_handler(logger)
    def save_chunks(self, chunks: List[Dict[str, Any]]):
        """Saves chunks to output dir"""
        input_name = os.path.splitext(self.input_filename)[0]  # Remove the extension
        output_filename = f"{input_name}-chunked.json"
        output_filepath = os.path.join(self.output_dir, output_filename)
        with open(output_filepath, 'w', encoding='utf-8') as f:
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
    def _create_metadata(self, page_metadata: Dict[str, Any], token_count: int) -> Dict[str, Any]:
        """Creates metadata dictionary for a chunk"""
        metadata = {
            'token_count': token_count,
            'source_url': page_metadata.get('sourceURL', ''),
            'page_title': page_metadata.get('title', '')
            # 'position_in_doc_hierarchy' removed as per your request
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
        self.original_content_tokens = 0
        self.content_missing = False
        self.chunk_token_counts = []
        self.headings_preserved = {'h1': set(), 'h2': set()}
        self.total_headings = {'h1': 0, 'h2': 0}

    def increment_total_headings(self, level):
        if level in self.total_headings:
            self.total_headings[level] += 1
        else:
            self.total_headings[level] = 1

    def add_preserved_heading(self, level, heading_text):
        if level not in self.headings_preserved:
            self.headings_preserved[level] = set()
        self.headings_preserved[level].add(heading_text)

    def add_chunk(self, token_count):
        self.total_chunks += 1
        self.total_tokens += token_count
        self.chunk_token_counts.append(token_count)

    def set_original_content_tokens(self, token_count):
        self.original_content_tokens = token_count

    def add_validation_error(self, error_message):
        self.validation_errors.append(error_message)

    def validate(self, chunks, original_content):
        self.validate_all_chunks(chunks, original_content)
        self.log_summary()
        self.find_incorrect_chunks(chunks)

    def validate_all_chunks(self, chunks: List[Dict[str, Any]], original_content: str):
        """Performs overall validation of chunks"""
        # Check if total tokens in chunks match the original content
        combined_chunk_content = ''.join(chunk['data']['text'] for chunk in chunks)
        if combined_chunk_content.strip() != original_content.strip():
            # Determine if content is missing
            original_length = len(original_content.strip())
            combined_length = len(combined_chunk_content.strip())
            length_difference = original_length - combined_length
            percentage_difference = (abs(length_difference) / original_length) * 100

            if length_difference > 0:
                self.content_missing = True
                self.validation_errors.append(
                    f"Content missing from chunks. Missing {length_difference} "
                    f"characters ({percentage_difference:.2f}%)."
                )
            else:
                self.content_missing = False

        # Check for duplicates and remove them carefully
        chunk_texts = {}
        duplicates_found = False
        cleaned_chunks = []
        for chunk in chunks:
            text = chunk['data']['text']
            if text in chunk_texts:
                duplicates_found = True
                # Duplicates are fixed here; no need to report them
                continue
            else:
                chunk_texts[text] = True
                cleaned_chunks.append(chunk)

        if duplicates_found:
            # Update the chunks list to the cleaned_chunks without duplicates
            chunks.clear()
            chunks.extend(cleaned_chunks)
            self.total_chunks = len(chunks)

    def log_summary(self):
        """Logs a concise summary of the chunking process"""
        # Token counts
        self.logger.info(f"Total tokens in original content: {self.original_content_tokens}")
        self.logger.info(f"Total tokens in chunks: {self.total_tokens}")
        token_difference = self.original_content_tokens - self.total_tokens
        percentage_difference = (
            (abs(token_difference) / self.original_content_tokens) * 100
            if self.original_content_tokens > 0 else 0
        )
        self.logger.info(
            f"Token difference: {token_difference} tokens ({percentage_difference:.2f}%)"
        )

        # Content alignment
        if self.content_missing:
            self.logger.warning(
                f"Content missing from chunks. Missing {token_difference} tokens "
                f"({percentage_difference:.2f}%)."
            )
        else:
            self.logger.info("All content has been preserved in the chunks.")

        # Total chunks
        self.logger.info(f"Total chunks created: {self.total_chunks}")

        # Chunk statistics
        if self.chunk_token_counts:
            avg_tokens = sum(self.chunk_token_counts) / len(self.chunk_token_counts)
            median_tokens = statistics.median(self.chunk_token_counts)
            min_tokens = min(self.chunk_token_counts)
            max_tokens = max(self.chunk_token_counts)
            p25 = statistics.quantiles(self.chunk_token_counts, n=4)[0]
            p75 = statistics.quantiles(self.chunk_token_counts, n=4)[2]
            self.logger.info("Chunk token statistics:")
            self.logger.info(f" - Average tokens per chunk: {avg_tokens:.2f}")
            self.logger.info(f" - Median tokens per chunk: {median_tokens}")
            self.logger.info(f" - Min tokens in a chunk: {min_tokens}")
            self.logger.info(f" - Max tokens in a chunk: {max_tokens}")
            self.logger.info(f" - 25th percentile tokens: {p25}")
            self.logger.info(f" - 75th percentile tokens: {p75}")
        else:
            self.logger.warning("No chunks to calculate statistics.")

        # Headers summary
        h1_preserved = len(self.headings_preserved.get('h1', set()))
        h2_preserved = len(self.headings_preserved.get('h2', set()))
        h1_total = self.total_headings.get('h1', 0)
        h2_total = self.total_headings.get('h2', 0)
        h1_percentage = (h1_preserved / h1_total * 100) if h1_total > 0 else 0
        h2_percentage = (h2_preserved / h2_total * 100) if h2_total > 0 else 0
        self.logger.info(
            f"H1 headings preserved: {h1_preserved}/{h1_total} ({h1_percentage:.2f}%)"
        )
        self.logger.info(
            f"H2 headings preserved: {h2_preserved}/{h2_total} ({h2_percentage:.2f}%)"
        )

        # Validation errors
        unique_errors = set(self.validation_errors)
        if unique_errors:
            self.logger.warning(f"Validation issues encountered ({len(unique_errors)}):")
            for error in unique_errors:
                self.logger.warning(f"- {error}")
        else:
            self.logger.info("No validation issues encountered.")

    def find_incorrect_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Finds chunks below min_chunk_size or above max_tokens and saves to JSON."""
        incorrect = {
            "too_small": [
                {
                    "id": c["chunk_id"],
                    "size": c["metadata"]["token_count"],
                    'headers': c['data']['headers'],
                    'text': c['data']['text']
                }
                for c in chunks if c["metadata"]["token_count"] < self.min_chunk_size
            ],
            "too_large": [
                {
                    "id": c["chunk_id"],
                    "size": c["metadata"]["token_count"],
                    'headers': c['data']['headers'],
                    'text': c['data']['text']
                }
                for c in chunks if c["metadata"]["token_count"] > self.max_tokens
            ]
        }

        if incorrect["too_small"] or incorrect["too_large"]:
            base_name = os.path.splitext(self.input_filename)[0]
            output_filename = f"{base_name}-incorrect-chunks.json"
            output_filepath = os.path.join(self.output_dir, output_filename)

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(incorrect, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Incorrect chunks saved to {output_filepath}")
            self.logger.info(f"Number of too small chunks: {len(incorrect['too_small'])}")
            self.logger.info(f"Number of too big chunks: {len(incorrect['too_large'])}")
        else:
            self.logger.info("No incorrect chunks found.")




# Test usage
def main():
    markdown_chunker = MarkdownChunker(input_filename="cra_docs_en_20240912_082455.json")
    result = markdown_chunker.load_data()
    chunks = markdown_chunker.process_pages(result)
    markdown_chunker.save_chunks(chunks)

if __name__ == "__main__":
    main()