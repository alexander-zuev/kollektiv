from os import listdir
from os.path import isfile, join

from src.crawling.crawler import CrawlJobStatus, CrawlRequest, CrawlResult, FireCrawlAPIError, FireCrawler
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
    async def initialize(self) -> ClaudeAssistant:
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
            await self.vector_db.add_documents(documents, file)

        claude_assistant.update_system_prompt(self.summarizer.get_all_summaries())

        reranker = Reranker()
        retriever = ResultRetriever(vector_db=self.vector_db, reranker=reranker)
        claude_assistant.retriever = retriever

        logger.info("Components initialized successfully.")
        return claude_assistant

    @staticmethod
    def _get_crawl_message(crawl_result: CrawlResult) -> str:
        if crawl_result.job_status == CrawlJobStatus.COMPLETED:
            message = f"""
            ✅ Crawl completed successfully!\n
            Extracted results from {len(crawl_result.data)} pages, starting from {crawl_result.url} in
            {crawl_result.time_taken:.2f} seconds.\n
            """
            return message
        elif crawl_result.job_status == CrawlJobStatus.FAILED:
            message = """
            ❌ Crawl request failed! Please try again."""
            return message
        else:
            return "Unknown error occurred, please try again."

    async def handle_crawl(self, crawl_inputs: dict) -> tuple[CrawlResult, str]:
        """Crawls the url provided by the user and returns filename"""
        crawl_request = CrawlRequest(
            url=crawl_inputs["url"],
            page_limit=crawl_inputs["num_pages"],
            exclude_patterns=crawl_inputs["exclude_patterns"],
        )

        try:
            job = await self.crawler.crawl(crawl_request)
            logger.info("Crawl job started successfully.")

            success_message = f"""
            ✅ Crawl job started successfully!\n
            Job ID: {job.id}\n
            Progress will be tracked via webhooks.\n
            """
            return job, success_message

        except FireCrawlAPIError as e:
            logger.error(f"API error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"An unhandled error occurred: {e}")
            raise

    async def prepare_chunks(self, crawl_results: CrawlResult) -> tuple[str, str]:
        """Conducts chunking and returns the filename of the chunked file."""
        try:
            result = self.chunker.load_data(filename=crawl_results.filename)
            chunks = self.chunker.process_pages(result)
            chunk_filename = self.chunker.save_chunks(chunks)
            message = """
            ✅Chunking completed successfully!\n"""
            return chunk_filename, message
        except Exception as e:
            logger.error(f"An unhandled error occurred: {e}")
            raise

    async def embed_and_store(self, filename) -> str:
        try:
            vector_db_reader = DocumentProcessor()
            docs = vector_db_reader.load_json(filename)
            await self.vector_db.add_documents(docs, filename)
            summary = ""
        except Exception as e:
            logger.error(f"An unhandled error occured: {e}")
            raise

    def extract_file_summary(self, filename: str) -> str:
        """Generates summary of the added file"""
        pass

    @base_error_handler
    async def index_web_content(self, crawl_inputs: dict) -> str:
        """Orchestrates the document crawling, chunking, embedding, and summarization."""
        logger.info("Starting indexing of new content. This might take a while")

        # Step 1 - Get crawl results
        crawl_results, message = await self.handle_crawl(crawl_inputs)
        yield message

        # TODO: implement custom exception classes for crawler exceptions
        # Step 2 - Chunk the crawling results
        chunks_filename, message = await self.prepare_chunks(crawl_results)
        yield message

        # Step 3 - Embed and store them
        summary, message = await self.embed_and_store(chunks_filename)

        # Step 4 - Inform the user on the results.

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

    async def process_file(self, filename: str) -> None:
        """Process the given file and generate summaries.

        Args:
            filename (str): The name of the file to process.
        """
        # ... rest of the method
