from os import listdir
from os.path import isfile, join

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import PROCESSED_DATA_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, SummaryManager, VectorDB

logger = get_logger()


class ComponentInitializer:

    def __init__(self, reset_db: bool = False, load_all_docs: bool = False, files: list[str] | None = None):
        self.reset_db = reset_db
        self.files_dir = PROCESSED_DATA_DIR
        self.files = files if files is not None else []
        self.load_all = load_all_docs

    def load_all_docs(self) -> list[str]:
        """Loads all docs into the system"""
        return [f for f in listdir(self.files_dir) if isfile(join(self.files_dir, f))]

    def load_selected_docs(self) -> list[str]:
        """Loads only user-selected docs into the system"""
        return self.files

    @base_error_handler
    def init(self):
        logger.info("Initializing components...")

        vector_db = VectorDB()
        reader = DocumentProcessor()

        if self.reset_db:
            logger.info("Resetting database...")
            vector_db.reset_database()

        summary_manager = SummaryManager()

        claude_assistant = ClaudeAssistant(vector_db=vector_db)

        if self.load_all:
            docs_to_load = self.load_all_docs()
        else:
            docs_to_load = self.load_selected_docs()

        for file in docs_to_load:
            documents = reader.load_json(file)
            vector_db.add_documents(documents, file)

        claude_assistant.update_system_prompt(summary_manager.get_all_summaries())

        reranker = Reranker()
        retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)
        claude_assistant.retriever = retriever

        logger.info("Components initialized successfully.")
        return claude_assistant
