# app.py
import logging

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.logger import set_log_level, setup_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, VectorDB

# Define DEBUG flag
DEBUG = False  # Set to False to switch to INFO level

# Set the global log level based on DEBUG
if DEBUG:
    set_log_level(logging.DEBUG)


def main():
    # Initialize logger
    logger = setup_logger("app", "app.log")

    # Initialize components
    vector_db = VectorDB()
    # vector_db.reset_database()
    claude_assistant = ClaudeAssistant()

    # Load documents
    file_names = [
        # Uncomment or add file names as needed
        # "cra_docs_en_20240912_082455-chunked.json",
        # "supabase_com_docs_guides_auth_20240916_235100-chunked.json",
        # "cra_supabase_docs_20240911_071611-chunked.json",
        # "docs_llamaindex_ai_en_stable_20240917_090349-chunked.json"
        "supabase_com_docs_guides_ai_20240917_103658-chunked.json"
    ]
    for file_name in file_names:
        document_loader = DocumentProcessor(file_name)
        json_data = document_loader.load_json()
        vector_db.add_documents(json_data, claude_assistant)

    reranker = Reranker()
    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)

    # Set retriever in the assistant
    claude_assistant.retriever = retriever

    logger.info("Application successfully initialized.")

    # Start interaction loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        response = claude_assistant.generate_response(user_input)
        print(f"Assistant: {response}")


if __name__ == "__main__":
    main()
