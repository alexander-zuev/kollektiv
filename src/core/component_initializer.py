import logging

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.logger import setup_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, VectorDB


class ComponentInitializer:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.logger = setup_logger(__name__, "app.log", level=logging.DEBUG if debug else logging.INFO)

    def initialize(self):
        self.logger.info("Initializing components...")
        vector_db = VectorDB()
        # vector_db.reset_database()
        claude_assistant = ClaudeAssistant()

        files_to_load = [
            "supabase_com_docs_guides_ai_20240917_103658-chunked.json",
            "docs_anthropic_com_en_docs_20240922_174102-chunked.json",
            "docs_llamaindex_ai_en_stable_20240917_090349-chunked.json",
            "docs_llamaindex_ai_en_stable_examples_20240922_173959-chunked.json",
            "langchain-ai_github_io_langgraph_how-tos_20240922_174234-chunked.json",
        ]
        for file_name in files_to_load:
            document_loader = DocumentProcessor(file_name)
            json_data = document_loader.load_json()
            vector_db.add_documents(json_data, claude_assistant, file_name)

        reranker = Reranker()
        retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)
        claude_assistant.retriever = retriever

        self.logger.info("Components initialized successfully.")
        return claude_assistant
