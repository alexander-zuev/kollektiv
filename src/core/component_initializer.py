from os import listdir
from os.path import isfile, join

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import PROCESSED_DATA_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, SummaryManager, VectorDB

logger = get_logger()


class ComponentInitializer:
    """
    Handles the initialization of components for document processing and system setup.

    Args:
        reset_db (bool): Determines whether to reset the database during initialization. Defaults to False.
        load_all_docs (bool): Flag to load all documents or only user-selected ones. Defaults to False.
        files (list[str] | None): List of selected file names to load. Defaults to None.

    Methods:
        load_all_docs: Loads all docs into the system.
        load_selected_docs: Loads only user-selected docs into the system.
        init: Initializes all components, including database, document processor, and assistant.

    Returns:
        ClaudeAssistant: The initialized assistant with components ready for interaction.

    Raises:
        Any exceptions raised within the @base_error_handler decorator.
    """

    def __init__(self, reset_db: bool = False, load_all_docs: bool = False, files: list[str] | None = None):
        self.reset_db = reset_db
        self.chunked_docs_dir = PROCESSED_DATA_DIR
        self.files = files if files is not None else []
        self.load_all = load_all_docs

    def load_all_docs(self) -> list[str]:
        """
        Load all documents from the directory specified by `self.chunked_docs_dir`.

        Returns:
            list[str]: A list of filenames found in the directory.
        """
        return [f for f in listdir(self.chunked_docs_dir) if isfile(join(self.chunked_docs_dir, f))]

    def load_selected_docs(self) -> list[str]:
        """
        Loads a list of selected documents.

        Returns:
            list[str]: A list of file names representing the selected documents.
        """
        return self.files

    @base_error_handler
    def init(self):
        """
        Initializes the components and sets up the ClaudeAssistant.

        Args:
            self: An instance of the class containing the initialization method.

        Returns:
            ClaudeAssistant: An instance of ClaudeAssistant configured with initialized components.

        Raises:
            Exception: If there is an error during component initialization.
        """
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
