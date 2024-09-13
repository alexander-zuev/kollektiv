import uuid
import json
import os
import re
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
        # For validation summary
        self.validation_errors = []
        self.total_chunks = 0
        self.total_tokens = 0
        self.content_preserved = True

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
            all_chunks.extend(chunks)

        # After processing all pages, perform validation
        self.validate_all_chunks(all_chunks, original_content)
        return all_chunks

    @error_handler(logger)
    def identify_sections(self, page_content: str, page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identifies sections in the page content based on headers"""
        sections = []

        # Patterns for headers
        h_pattern = re.compile(r'^(#{1,6}) (.*)', re.MULTILINE)

        # Find all headers
        headers = [(m.start(), m.group(1), m.group(2).strip()) for m in h_pattern.finditer(page_content)]
        headers.sort()

        # If no headers found, treat the entire content as one section
        if not headers:
            sections.append({
                "headers": {
                    "h1": page_metadata.get('title', 'Untitled')
                },
                "content": page_content.strip()
            })
            self.logger.warning(f"No headers found in page. Using page title as h1.")
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

        for idx, (pos, header_marker, header_text) in enumerate(headers):
            header_level = len(header_marker)
            header = header_text

            # Extract content before this header
            content = page_content[last_index:pos].strip()
            if content:
                current_section['content'] = content
                sections.append(current_section.copy())
                current_section['content'] = ""

            # Update headers based on header level
            if header_level == 1:
                current_section['headers']['h1'] = header
                current_section['headers']['h2'] = ""
                current_section['headers']['h3'] = ""
            elif header_level == 2:
                current_section['headers']['h2'] = header
                current_section['headers']['h3'] = ""
            elif header_level == 3:
                current_section['headers']['h3'] = header

            last_index = pos + len(header_marker) + 1 + len(header_text)  # +1 for space after #

        # Add remaining content after the last header
        content = page_content[last_index:].strip()
        if content:
            current_section['content'] = content
            sections.append(current_section.copy())

        return sections

    @error_handler(logger)
    def create_chunks(self, sections: List[Dict[str, Any]], page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        for section in sections:
            section_chunks = self._split_section(section['content'], section['headers'])
            for chunk in section_chunks:
                chunk_id = str(self._generate_chunk_id())
                token_count = self._calculate_tokens(chunk['content'])
                self.total_tokens += token_count
                metadata = self._create_metadata(page_metadata, token_count, chunk['headers'])
                new_chunk = {
                    'chunk_id': chunk_id,
                    'metadata': metadata,
                    'data': {
                        'headers': chunk['headers'],
                        'text': chunk['content']
                    }
                }
                chunks.append(new_chunk)
                self.total_chunks += 1

        self._add_overlap(chunks)
        return chunks

    @error_handler(logger)
    def _split_section(self, content: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        chunks = []
        current_chunk = {'headers': headers.copy(), 'content': ''}
        lines = content.split('\n')
        in_code_block = False

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('```'):
                # Start or end of code block
                in_code_block = not in_code_block

            # Calculate token count if we add this line
            potential_chunk_content = current_chunk['content'] + line + '\n'
            token_count = self._calculate_tokens(potential_chunk_content)

            if token_count <= self.soft_token_limit or in_code_block:
                current_chunk['content'] += line + '\n'
            else:
                # If in code block, we need to handle this carefully
                if in_code_block:
                    # Code block exceeds soft limit, check against hard limit
                    if token_count <= self.max_tokens:
                        current_chunk['content'] += line + '\n'
                    else:
                        self.validation_errors.append(f"Code block exceeds hard token limit in headers {headers}")
                        self.logger.error(f"Code block exceeds hard token limit in headers {headers}")
                        # You may choose to handle this differently
                else:
                    # Save current chunk
                    if current_chunk['content'].strip():
                        chunks.append(current_chunk.copy())
                    current_chunk = {'headers': headers.copy(), 'content': line + '\n'}

        # Add any remaining content
        if current_chunk['content'].strip():
            chunks.append(current_chunk.copy())

        # Ensure chunks meet minimum size and adjust if necessary
        adjusted_chunks = self._adjust_chunks(chunks)
        return adjusted_chunks

    @error_handler(logger)
    def _adjust_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adjust chunks to ensure they meet min and max token requirements"""
        adjusted_chunks = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            token_count = self._calculate_tokens(chunk['content'])

            if token_count < self.min_chunk_size and i > 0:
                # Merge with previous chunk
                prev_chunk = adjusted_chunks[-1]
                prev_chunk['content'] += chunk['content']
                prev_headers = prev_chunk['headers']
                curr_headers = chunk['headers']
                # Update headers if necessary
                for key in ['h1', 'h2', 'h3']:
                    if curr_headers.get(key) and curr_headers.get(key) != prev_headers.get(key):
                        prev_headers[key] = curr_headers[key]
                adjusted_chunks[-1] = prev_chunk
            else:
                adjusted_chunks.append(chunk)
            i += 1
        return adjusted_chunks

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
            overlap_token_count = max(int(self._calculate_tokens(prev_chunk_text) * self.overlap_percentage), min_overlap_tokens)
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
            self.content_preserved = False
            self.validation_errors.append("Content mismatch between original and chunks.")
            self.logger.error("Content mismatch between original and chunks.")
        else:
            self.content_preserved = True

        # Check for duplicates
        chunk_texts = set()
        duplicates_found = False
        for chunk in chunks:
            text = chunk['data']['text']
            if text in chunk_texts:
                duplicates_found = True
                self.validation_errors.append(f"Duplicate chunk found with chunk_id {chunk['chunk_id']}")
                self.logger.error(f"Duplicate chunk found with chunk_id {chunk['chunk_id']}")
            else:
                chunk_texts.add(text)

        # Summarize validation
        if self.validation_errors:
            self.logger.warning(f"Chunking completed with {len(self.validation_errors)} issues.")
        else:
            self.logger.info("Chunking completed successfully with no issues.")

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
    def _create_metadata(self, page_metadata: Dict[str, Any], token_count: int, headers: Dict[str, str]) -> Dict[str, Any]:
        """Creates metadata dictionary for a chunk"""
        position_in_doc_hierarchy = " > ".join([v for k, v in headers.items() if v])
        metadata = {
            'token_count': token_count,
            'source_url': page_metadata.get('sourceURL', ''),
            'page_title': page_metadata.get('title', ''),
            'position_in_doc_hierarchy': position_in_doc_hierarchy
        }
        return metadata

    def log_summary(self):
        """Logs a summary of the chunking process"""
        self.logger.info(f"Total chunks created: {self.total_chunks}")
        self.logger.info(f"Total tokens in chunks: {self.total_tokens}")
        if self.content_preserved:
            self.logger.info("Content preservation check passed.")
        else:
            self.logger.warning("Content preservation check failed.")
        if self.validation_errors:
            self.logger.warning("Validation issues encountered:")
            for error in self.validation_errors:
                self.logger.warning(f"- {error}")
        else:
            self.logger.info("No validation issues encountered.")

# Test usage
def main():
    markdown_chunker = MarkdownChunker(input_filename="cra_docs_en_20240912_082455.json")
    result = markdown_chunker.load_data()
    chunks = markdown_chunker.process_pages(result)
    markdown_chunker.save_chunks(chunks)
    markdown_chunker.log_summary()

if __name__ == "__main__":
    main()