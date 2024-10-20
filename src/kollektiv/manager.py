from os import listdir
from os.path import isfile, join

from src.crawling.crawler import FireCrawler
from src.generation.claude_assistant import ClaudeAssistant
from src.processing.chunking import MarkdownChunker
from src.utils.config import PROCESSED_DATA_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger
from src.vector_storage.vector_db import DocumentProcessor, Reranker, ResultRetriever, SummaryManager, VectorDB

logger = get_logger()


# TODO: refactor and remove. Load all documents by default.
class Kollektiv:
    """
    The central orchestrator, managing the flow of documents through crawling, chunking, embedding, and summarization.

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

    def __init__(
        self,
        crawler: FireCrawler,
        chunker: MarkdownChunker,
        vector_db: VectorDB,
        summarizer: SummaryManager,
        reset_db: bool = False,
        load_all_docs: bool = False,
        files: list[str] | None = None,
    ):
        self.reset_db = reset_db
        self.chunked_docs_dir = PROCESSED_DATA_DIR
        self.files = files if files is not None else []
        self.load_all = load_all_docs
        self.crawler = crawler
        self.chunker = chunker
        self.vector_db = vector_db
        self.summarizer = summarizer

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

        if self.reset_db:
            logger.info("Resetting database...")
            self.vector_db.reset_database()

        claude_assistant = ClaudeAssistant(vector_db=self.vector_db)

        if self.load_all:
            docs_to_load = self.load_all_docs()
        else:
            docs_to_load = self.load_selected_docs()

        reader = DocumentProcessor()
        for file in docs_to_load:
            documents = reader.load_json(file)
            self.vector_db.add_documents(documents, file)

        claude_assistant.update_system_prompt(self.summarizer.get_all_summaries())

        reranker = Reranker()
        retriever = ResultRetriever(vector_db=self.vector_db, reranker=reranker)
        claude_assistant.retriever = retriever

        logger.info("Components initialized successfully.")
        return claude_assistant

    def add_document(self, url: str) -> str:
        """Adds documents that were parsed."""
        # Placeholder for document addition logic
        return f"Adding document from URL: {url}"

    def remove_document(self, doc_id: str) -> str:
        """Removes documents that were parsed."""
        # Placeholder for document removal logic
        return f"Removing document with ID: {doc_id}"

    def list_documents(self) -> str:
        """Returned all loaded documents."""
        # Placeholder for document listing logic
        return "Listing all documents"
