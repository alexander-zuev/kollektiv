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

        print("Printing sections debuggins")
        print(sections)
            # page_chunks = self.create_chunks(sections, page_metadata)
            # all_chunks.extend(page_chunks)


        # calls create chunks for each section
        # returns a list of chunks for all pages

    @error_handler(logger)
    def identify_sections(self, page_content: str) -> List[Dict[str, Any]]:
        """Takes a singple page content and identifies headers"""
        # parses markdown to identify H1, H2 headers
        # returns a list of all sections with their headers and content
        sections = []
        h1_pattern = re.compile(r'^# (.+)$', re.MULTILINE)
        h2_pattern = re.compile(r'^## (.+)$', re.MULTILINE)

        h1_match = h1_pattern.search(page_content)
        h1_title = h1_match.group(1) if h1_match else ""

        h2_splits = h2_pattern.split(page_content)

        if h1_title and h2_splits[0].strip():
            sections.append({
                "headers": {"h1": h1_title},
                "content": h2_splits[0].strip()
            })

        for i in range(1, len(h2_splits), 2):
            sections.append({
                "headers": {"h1": h1_title, "h2": h2_splits[i]},
                "content": h2_splits[i + 1].strip()
            })

        return sections

    @error_handler(logger)
    def create_chunks(self, sections, page_metadata: Dict[str, Any]):
        """Takes a section (content between headers) and chunks it"""
        # splits the content based on token limits
        # creates metadata
        # handles overlap
        # calls handle_code_blocks for each chunks
        # returns a list of chunk dictionaries

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
            'source_url' : page_metadata['sourceUrl'],
            'page_title' : page_metadata['title'],
        }
        return metadata

    @error_handler(logger)
    def _create_overlap(self):
        """Handles overlap between chunks"""

# Test usage
markdown_chunker = MarkdownChunker(input_filename="cra_supabase_docs_2024-09-11 07:16:11.json")
result = markdown_chunker.load_data()
# print(result['data'][0]['markdown'])
markdown_chunker.process_pages(result)