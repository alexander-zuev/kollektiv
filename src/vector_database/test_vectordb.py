import json
from src.vector_database.chroma_db import VectorDB
from src.utils.config import PERSIST_DIRECTORY, PROCESSED_DATA_DIR
from src.utils.logger import setup_logger
import os

logger = setup_logger(__name__, 'generate_and_query_db.log')

def main():
    # Initialize VectorDB
    db = VectorDB(PERSIST_DIRECTORY)

    # Load processed data
    with open(os.path.join(PROCESSED_DATA_DIR, 'processed_supabase_docs_20240901_193122.json'), 'r') as f:
        processed_data = json.load(f)

    # Add chunks to the database
    db.add(processed_data['chunks'])
    logger.info(f"Added {len(processed_data['chunks'])} chunks to the database.")

    # Perform a test query
    query = "How to upsert data in Supabase?"
    results = db.query(query_texts=[query], n_results=3)

    logger.info(f"Query: {query}")
    logger.info(f"Results: {results}")

if __name__ == "__main__":
    main()