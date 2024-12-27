import asyncio
from typing import Union

from src.core.content.chunker import MarkdownChunker
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.vector_db import VectorDB
from src.infra.data.data_repository import DataRepository
from src.infra.external.chroma_client import ChromaClient
from src.infra.external.supabase_client import SupabaseClient
from src.infra.logger import get_logger
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class WorkerServices:
    """Services singleton necessary for RQ worker."""

    _instance: Union["WorkerServices", None] = None

    def __init__(self) -> None:
        logger.info("Initializing services...")

        # Initialize sync services
        self.chunker = MarkdownChunker()
        self.embedding_manager = EmbeddingManager()

        # Initialize async services
        self.chroma_client = asyncio.run(ChromaClient().create_client())
        self.supabase_client = asyncio.run(SupabaseClient().get_client())

        # Initialize dependent services
        self.vector_db = VectorDB(chroma_client=self.chroma_client, embedding_manager=self.embedding_manager)
        self.repository = DataRepository(db_client=self.supabase_client)
        self.data_service = DataService(repository=self.repository)
        self.job_manager = JobManager(data_service=self.data_service)

    @classmethod
    def get_instance(cls) -> "WorkerServices":
        """Get the singleton instance of Services."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
