from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import VectorDB, Reranker, ResultRetriever, DocumentProcessor
from src.utils.logger import setup_logger

def main():
    # Initialize logger
    logger = setup_logger('app', "app.log")

    # Initialize components
    vector_db = VectorDB()

    # let's load some docs
    file_names = ["cra_docs_en_20240912_082455-chunked.json", "cra_docs_en_20240914_172207-chunked.json"]  # Add all document file names
    for file_name in file_names:
        document_loader = DocumentProcessor(file_name)
        json_data = document_loader.load_json()
        vector_db.add_documents(json_data)


    reranker = Reranker()

    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)

    claude_assistant = ClaudeAssistant()
    # Update Claude's system prompt with all document summaries
    claude_assistant.update_system_prompt(vector_db.get_document_summaries())

    # Set retriever in the assistant
    claude_assistant.retriever = retriever

    # Start interaction loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        response = claude_assistant.generate_response(user_input)
        print(f"Assistant: {response}")

if __name__ == "__main__":
    main()