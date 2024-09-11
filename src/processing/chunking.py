import uuid
from pprint import pprint
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
            self.logger.info(f"Processing page {index + 1} of {len(json_input['data'])}")

            sections = self.identify_sections(page_content)
            chunks = self.create_chunks(sections, page_metadata)
            all_chunks.extend(chunks)


        print("Debugging the results")
        for item in all_chunks:
            print(item)


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
                chunk_id = self._generate_chunk_id()
                chunk['chunk_id'] = chunk_id
                chunk['metadata'] = self._create_metadata(page_metadata)
                chunk['metadata']['token_count'] = self._calculate_tokens(chunk['content'])
                chunks.append(chunk)

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
    def save_chunks(self):
        """Saves chunks to output dir"""
        # takes the final list of chunks
        # saves them to the output director in the specified JSON format


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
    def _create_metadata(self, page_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Creates metadata dictionary for a chunk"""
        metadata = {
            'token_count': 0,
            'source_url' : page_metadata['sourceURL'],
            'page_title' : page_metadata['title'],
        }
        return metadata

    @error_handler(logger)
    def _add_overlap(self, chunks: List[Dict[str, Any]]) -> None:
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            overlap_text = prev_chunk['content'][-int(len(prev_chunk['content']) * self.overlap_percentage):]
            curr_chunk['metadata']['overlap'] = {
                'previous_chunk_id': prev_chunk['chunk_id'],
                'text': overlap_text
            }

# Test usage
markdown_chunker = MarkdownChunker(input_filename="cra_supabase_docs_2024-09-11 07:16:11.json")
result = markdown_chunker.load_data()
# print(result['data'][0]['markdown'])
markdown_chunker.process_pages(result)