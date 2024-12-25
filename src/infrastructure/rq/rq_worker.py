import asyncio

from rq import Queue
from rq.worker import Worker

from src.core.content.chunker import MarkdownChunker
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.logger import configure_logging, get_logger
from src.infrastructure.config.settings import settings
from src.infrastructure.external.chroma_client import ChromaClient
from src.infrastructure.external.redis_client import RedisClient
from src.infrastructure.external.supabase_client import SupabaseClient
from src.infrastructure.storage.data_repository import DataRepository
from src.services.data_service import DataService
from src.services.job_manager import JobManager

configure_logging(debug=True)
logger = get_logger()

logger.info("Starting RQ worker")


class WorkerServices:
    """Services singleton necessary for RQ worker."""

    _instance = None

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

        # Redis
        self.redis_client = RedisClient().sync_client
        self.queue = Queue(name=settings.redis_queue_name, connection=self.redis_client)

    @classmethod
    def get_instance(cls) -> "WorkerServices":
        """Get the singleton instance of Services."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Initialize services before worker starts
services = WorkerServices.get_instance()


# Start worker with retry logic
def start_worker() -> None:
    """Start worker with retry logic."""
    redis_client = RedisClient().sync_client
    worker = Worker([settings.redis_queue_name], connection=redis_client)
    logger.info(f"Starting worker on queue: {settings.redis_queue_name}")
    worker.work()


if __name__ == "__main__":
    start_worker()
