# app.py
import logging

from colorama import Fore, Style, init

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.logger import set_log_level, setup_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, VectorDB

# Initialize colorama
init(autoreset=True)

# Define DEBUG flag
DEBUG = False  # Set to False to switch to INFO level

# Set the log level based on DEBUG flag
set_log_level(logging.DEBUG if DEBUG else logging.INFO)


def main():
    # Initialize logger
    logger = setup_logger("app", "app.log")

    # Initialize components
    vector_db = VectorDB()
    # vector_db.reset_database() # TODO: re-factor the setup
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
        user_input = input(f"{Fore.GREEN}You:{Style.RESET_ALL} ")
        if user_input.lower() in ["exit", "quit"]:
            break

        print(f"\n{Fore.BLUE}Assistant:{Style.RESET_ALL} ", end="", flush=True)
        response = claude_assistant.generate_response(user_input, stream=True)

        for text in response:
            if text.startswith("\n[Using tool:"):
                tool_name = text.split(":")[1].strip()[:-1]
                print(f"\n{Fore.YELLOW}[Using tool: {tool_name}]{Style.RESET_ALL}")
            else:
                print(text, end="", flush=True)
        print()  # Add a newline after the complete response

        # response = claude_assistant.generate_response(user_input, stream=True)
        # print("Assistant: ", end="")
        # for text in response:
        #     print(text, end="", flush=True)


if __name__ == "__main__":
    main()
