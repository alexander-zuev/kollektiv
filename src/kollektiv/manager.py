import os
from os import listdir
from os.path import isfile, join

from src.crawling.crawler import FireCrawler
from src.generation.claude_assistant import ClaudeAssistant
from src.interface.command_handler import CommandHandler
from src.interface.flow_manager import UserInputManager
from src.interface.message_handler import MessageHandler
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
    def initialize(self) -> ClaudeAssistant:
        """
        Initializes the components and sets up the ClaudeAssistant.

        Returns:
            ClaudeAssistant: An instance of ClaudeAssistant configured with initialized components.
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

    # TODO: abstract CrawlInputs and CrawlOutputs
    async def crawl(self, crawl_inputs: dict) -> str:
        """Crawls the url provided by the user and returns filename"""
        url = crawl_inputs["url"]
        num_pages = crawl_inputs["num_pages"]
        exclude_patterns = crawl_inputs["exclude_patterns"] or []

        logger.info(
            f"Adding document from URL: {url} with max pages: {num_pages} and exclude patterns:" f" {exclude_patterns}"
        )

        crawl_results = await self.crawler.async_crawl_url

    def chunk(self, filename: str) -> str:
        """Conducts chunking and returns the filename of the chunked file."""
        pass

    def store_new_documents(self, filename) -> str:
        pass

    def extract_file_summary(self, filename: str) -> str:
        """Generates summary of the added file"""
        pass

    @base_error_handler
    async def index_web_content(self, crawl_inputs: dict) -> str:
        """Orchestrates the document crawling, chunking, embedding, and summarization."""
        logger.info("Starting indexing of new content. This might take a while")

        # Step 1 - Get crawl results
        crawl_results = await self.crawl(crawl_inputs)
        pass

    def remove_document(self, doc_id: str) -> str:
        """Removes documents that were parsed."""
        # Placeholder for document removal logic
        return f"Removing document with ID: {doc_id}"

    def list_documents(self) -> str:
        """Returned all loaded documents."""
        # Placeholder for document listing logic
        return "Listing all documents"

    @classmethod
    @base_error_handler
    def setup(cls, reset_db: bool = False, load_all_docs: bool = False) -> MessageHandler:
        """
        Factory method to set up the Kollektiv system along with FlowManager, CommandHandler, and MessageHandler.

        Args:
            reset_db (bool): Whether to reset the vector database.
            load_all_docs (bool): Whether to load all documents.

        Returns:
            MessageHandler: An instance of MessageHandler initialized with all components.
        """
        logger.info("Setting up Kollektiv system...")

        # Determine files to load
        docs_to_load = [f for f in listdir(PROCESSED_DATA_DIR) if isfile(join(PROCESSED_DATA_DIR, f))]

        # Initialize components
        crawler = FireCrawler()
        chunker = MarkdownChunker()
        vector_db = VectorDB()
        summarizer = SummaryManager()

        # Create Kollektiv instance
        kollektiv = cls(
            crawler=crawler,
            chunker=chunker,
            vector_db=vector_db,
            summarizer=summarizer,
            reset_db=reset_db,
            load_all_docs=load_all_docs,
            files=docs_to_load,
        )

        # Initialize Kollektiv components
        claude_assistant = kollektiv.initialize()

        # Initialize FlowManager separately
        flow_manager = UserInputManager()

        # Initialize CommandHandler with separate FlowManager
        command_handler = CommandHandler(kollektiv, flow_manager)

        # Initialize MessageHandler with CommandHandler and FlowManager
        message_handler = MessageHandler(claude_assistant, command_handler)

        logger.info("Kollektiv system setup completed.")
        return message_handler
