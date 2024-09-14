from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import VectorDB, Reranker, ResultRetriever, DocumentProcessor
from src.utils.logger import setup_logger

def main():
    # Initialize logger
    logger = setup_logger('app', "app.log")

    # Initialize components
    vector_db = VectorDB()

    # let's load some docs
    filename = "cra_docs_en_20240912_082455-chunked.json"
    doc_processor = DocumentProcessor(filename)
    data = doc_processor.load_json()
    chunks = doc_processor.prepare_documents(data)
    vector_db.add_documents(chunks)


    reranker = Reranker()

    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)

    claude_assistant = ClaudeAssistant()

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