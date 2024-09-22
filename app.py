# app.py
import logging

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.logger import setup_logger
from src.utils.output_formatter import print_assistant_message
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, VectorDB

# Display all logging statements
DEBUG = True  # will display all logs


def main():
    # Initialize logger with the correct level based on DEBUG flag
    logger = setup_logger("app", "app.log", level=logging.DEBUG if DEBUG else logging.INFO)

    # Initialize components
    vector_db = VectorDB()
    # vector_db.reset_database()  # TODO: re-factor the setup
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
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            break

        response = claude_assistant.get_response(user_message, stream=True)
        print_assistant_message("Assistant: ", end="")
        # for text in response:
        #     print(text, end="", flush=True)
        for event in response:
            if event["type"] == "text":
                print(event["content"], end="", flush=True)
            elif event["type"] == "tool_use":
                print(f"\nUsing {event['tool']} tool 🧰.\n", end="", flush=True)
        print()  # Add a newline after the complete response


if __name__ == "__main__":
    main()
