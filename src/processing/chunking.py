import uuid
from pprint import pprint
import json
import os
import mistune
from typing import List, Dict, Any,

from src.utils.config import NEW_RAW_DATA_DIR, NEW_PROCESSED_DATA_DIR, LOG_DIR
from src.utils.logger import setup_logger
from src.utils.decorators import error_handler

logger = setup_logger('chunker', 'chunking.log')

class MarkdownChunker:
    def __init__(self, input_filename:str, output_dir: str = NEW_PROCESSED_DATA_DIR):
        self.output_dir = output_dir
        self.logger = logger
        self.input_filename = input_filename

    @error_handler
    def load_data(self) -> Dict[str, Any]:
        """Loads markdown from json and prepares for chunking"""
        input_filepath = os.path.join(NEW_RAW_DATA_DIR, self.input_filename)

        with open(input_filepath, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        self.logger.info(f"{self.input_filename} loaded")

        return doc

    @error_handler
    def save_chunks(self):
        """Saves chunks to output dir"""

    def identify_structure(self):
        """"""

    def _generate_chunk_id(self) -> uuid.UUID:
        """Generates chunk's uuidv4"""
        return uuid.uuid4()

    def _calculate_tokens(self, text: str) -> int:
        """Calculates the number of tokens in a given text using tiktoken"""

# Test usage
markdown_chunker = MarkdownChunker(input_filename="cra_supabase_docs_2024-09-08 22:21:45.json")
markdown_chunker.load_data()