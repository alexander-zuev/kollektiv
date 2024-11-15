# TODO: refactor and remove this service.
from os import listdir
from os.path import isfile, join

from src.api.chainlit.command_handler import CommandHandler
from src.api.chainlit.message_handler import MessageHandler
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.flow_manager import UserInputManager
from src.core.content.chunker import MarkdownChunker
from src.core.content.crawler.crawler import FireCrawler
from src.core.search.vector_db import DocumentProcessor, Reranker, ResultRetriever, SummaryManager, VectorDB
from src.core.system.job_manager import JobManager
from src.infrastructure.common.decorators import base_error_handler
from src.infrastructure.common.file_manager import FileManager
from src.infrastructure.config.logger import get_logger
from src.infrastructure.external.supabase_client import supabase_client
from src.infrastructure.storage.supabase.supabase_operations import DataRepository
from src.services.data_service import DataService

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
        self.chunked_docs_dir: str
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

    @classmethod
    @base_error_handler
    async def setup(cls, reset_db: bool = False, load_all_docs: bool = False) -> MessageHandler:
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
        db_client = supabase_client
        data_repo = DataRepository(db_client=self.db_client)
        data_service = DataService(datasource_repo=self.data_repo)
        job_manager = JobManager(data_service=data_service)
        file_manager = FileManager(raw_data_dir=RAW_DATA_DIR)
        crawler = FireCrawler(job_manager=job_manager, file_manager=file_manager)
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
        claude_assistant = await kollektiv.initialize()

        # Initialize FlowManager separately
        flow_manager = UserInputManager()

        # Initialize CommandHandler with separate FlowManager
        command_handler = CommandHandler(kollektiv, flow_manager)

        # Initialize MessageHandler with CommandHandler and FlowManager
        message_handler = MessageHandler.create(claude_assistant, command_handler)

        logger.info("Kollektiv system setup completed.")
        return message_handler
