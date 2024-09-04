import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from typing import List, Dict, Any
import json
import os


from src.utils.config import OPENAI_API_KEY, PERSIST_DIRECTORY, LOG_DIR
from src.utils.logger import setup_logger

# Set up logger
logger = setup_logger("vector_db", os.path.join(LOG_DIR, "vector_db.log"))

class DocumentProcessor