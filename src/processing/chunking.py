import uuid
import json
import os
from typing import List, Dict, Any
import tiktoken
import re

from src.utils.config import NEW_RAW_DATA_DIR, NEW_PROCESSED_DATA_DIR, LOG_DIR
from src.utils.logger import setup_logger
from src.utils.decorators import error_handler

logger = setup_logger('chunker', 'chunking.log')

class MarkdownChunker:
    def __init__(self,
                 input_filename:str,
                 output_dir: str = NEW_PROCESSED_DATA_DIR,
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

    @error_handler(logger)
    def load_data(self) -> Dict[str, Any]:
        """Loads markdown from json and prepares for chunking"""
        input_filepath = os.path.join(NEW_RAW_DATA_DIR, self.input_filename)

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
        # calls identify_sections for each page
        all_chunks = []
        for index, page in enumerate(json_input['data']):
            page_content = page['markdown']
            page_metadata = page['metadata']

            sections = self.identify_sections(page_content)
            chunks = self.create_chunks(sections, page_metadata)
            all_chunks.extend(chunks)

        return all_chunks


    @error_handler(logger)
    def identify_sections(self, page_content: str) -> List[Dict[str, Any]]:
        """Takes a single page content and identifies headers"""
        sections = []
        h1_pattern = re.compile(r'^# (.+)$', re.MULTILINE)
        h2_pattern = re.compile(r'^## (.+)$', re.MULTILINE)

        h1_match = h1_pattern.search(page_content)
        h1_title = h1_match.group(1) if h1_match else ""

        # Remove the H1 title from the content
        if h1_match:
            page_content = page_content[h1_match.end():].strip()

        h2_splits = h2_pattern.split(page_content)

        # Handle content between H1 and first H2
        if h2_splits[0].strip():
            sections.append({
                "headers": {"h1": h1_title},
                "content": h2_splits[0].strip()
            })

        # Handle H2 sections
        for i in range(1, len(h2_splits), 2):
            if i + 1 < len(h2_splits):
                sections.append({
                    "headers": {"h1": h1_title, "h2": h2_splits[i].strip()},
                    "content": h2_splits[i + 1].strip()
                })

        return sections

    @error_handler(logger)
    def create_chunks(self, sections: List[Dict[str, Any]], page_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        for section in sections:
            section_chunks = self._split_section(section['content'], section['headers'])
            for chunk in section_chunks:
                chunk_id = str(self._generate_chunk_id())
                token_count = self._calculate_tokens(chunk['content'])
                chunks.append({
                    'chunk_id': chunk_id,
                    'metadata': self._create_metadata(page_metadata, token_count),
                    'data': {
                        'headers': chunk['headers'],
                        'text': chunk['content']
                    }
                })

        self._add_overlap(chunks)
        return chunks

    @error_handler(logger)
    def _split_section(self, content: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        chunks = []
        current_chunk = {'headers': headers, 'content': ''}
        lines = content.split('\n')
        in_code_block = False

        for line in lines:
            if line.strip().startswith('`') and line.strip().endswith('`') and len(line.strip()) > 1:
                in_code_block = not in_code_block

            if in_code_block or self._calculate_tokens(current_chunk['content'] + line) <= self.soft_token_limit:
                current_chunk['content'] += line + '\n'
            else:
                if current_chunk['content'].strip():
                    chunks.append(current_chunk)
                current_chunk = {'headers': headers, 'content': line + '\n'}

            if not in_code_block and self._is_break_point(line):
                if self._calculate_tokens(current_chunk['content']) >= self.min_chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = {'headers': headers, 'content': ''}

        if current_chunk['content'].strip():
            chunks.append(current_chunk)

        return chunks

    @error_handler(logger)
    def _is_break_point(self, line: str) -> bool:
        # Check if the line is the end of a paragraph, list item, or other logical break point
        return line.strip() == '' or line.strip().endswith('.') or line.strip().endswith(':') or line.startswith(
            '- ') or line.startswith('* ')

    @error_handler(logger)
    def handle_code_blocks(self):
        """Identified code blocks within a chunk"""
        # Ensures code blocks are not split across chunks
        # Adjusts chunk boundaries, if necessary

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
            'source_url' : page_metadata['sourceURL'],
            'page_title' : page_metadata['title'],
        }
        return metadata

    @error_handler(logger)
    def _add_overlap(self,
                     chunks: List[Dict[str, Any]],
                     min_overlap_tokens: int = 50,
                     max_overlap_tokens: int = 50) -> None:

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            prev_chunk_text = prev_chunk['data']['text']
            prev_chunk_headers = prev_chunk['data']['headers']

            # Calculate 5% of the previous chunk's text
            overlap_text_length = int(len(prev_chunk_text) * self.overlap_percentage)
            overlap_text = prev_chunk_text[-overlap_text_length:]

            # Check if the overlap is less than MIN_OVERLAP_TOKENS
            if self._calculate_tokens(overlap_text) < min_overlap_tokens:
                # If the entire previous chunk is less than MAX_FULL_CHUNK_TOKENS, use it all
                if self._calculate_tokens(prev_chunk_text) <= max_overlap_tokens:
                    overlap_text = prev_chunk_text
                else:
                    # Otherwise, take the last MAX_FULL_CHUNK_TOKENS worth of text
                    overlap_text = self._get_last_n_tokens(prev_chunk_text, max_overlap_tokens)

            # Construct the overlap text with headers
            headers_text = " ".join(f"{k}: {v}" for k, v in prev_chunk_headers.items())
            full_overlap_text = f"Content of the previous chunk for context: {headers_text}\n\n{overlap_text}"

            curr_chunk['data']['overlap_text'] = {
                'previous_chunk_id': prev_chunk['chunk_id'],
                'text': full_overlap_text
            }

    def _get_last_n_tokens(self, text: str, n: int) -> str:
        tokens = self.tokenizer.encode(text)
        return self.tokenizer.decode(tokens[-n:])

# Test usage
def main():
    markdown_chunker = MarkdownChunker(input_filename="cra_supabase_docs_20240911_071611.json")
    result = markdown_chunker.load_data()
    # print(result['data'][0]['markdown'])
    chunks = markdown_chunker.process_pages(result)
    markdown_chunker.save_chunks(chunks)

if __name__ == "__main__":
    main()