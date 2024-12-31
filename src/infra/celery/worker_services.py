from typing import Union

from src.core.content.chunker import MarkdownChunker
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.vector_db import VectorDatabase
from src.infra.data.data_repository import DataRepository
from src.infra.data.redis_repository import RedisRepository
from src.infra.events.event_publisher import EventPublisher
from src.infra.external.chroma_manager import ChromaManager
from src.infra.external.redis_manager import RedisManager
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.logger import get_logger
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class WorkerServices:
    """Services singleton necessary for Celery worker."""

    _instance: Union["WorkerServices", None] = None

    def __init__(self) -> None:
        logger.info("Initializing worker services...")

        self.job_manager: JobManager | None = None
        self.data_service: DataService | None = None
        self.repository: DataRepository | None = None
        self.supabase_manager: SupabaseManager | None = None
        self.vector_db: VectorDatabase | None = None
        self.redis_manager: RedisManager | None = None
        self.async_redis_manager: RedisManager | None = None
        self.redis_repository: RedisRepository | None = None
        self.embedding_manager: EmbeddingManager | None = None
        self.chroma_manager: ChromaManager | None = None
        self.event_publisher: EventPublisher | None = None
        self.chunker: MarkdownChunker | None = None

    async def initialize_services(self) -> None:
        """Initialize all necesssary worker services."""
        try:
            # Database & Repository
            self.supabase_manager = await SupabaseManager.create_async()
            self.repository = DataRepository(supabase_manager=self.supabase_manager)
            self.data_service = DataService(repository=self.repository)

            # Redis
            self.async_redis_manager = await RedisManager.create_async()
            self.redis_repository = RedisRepository(manager=self.async_redis_manager)

            # Job & Content Services
            self.job_manager = JobManager(data_service=self.data_service)
            self.chunker = MarkdownChunker()

            # Vector operations
            self.chroma_manager = await ChromaManager.create_async()
            self.embedding_manager = EmbeddingManager()
            self.vector_db = VectorDatabase(
                chroma_manager=self.chroma_manager,
                embedding_manager=self.embedding_manager,
                data_service=self.data_service,
            )

            # Events
            self.event_publisher = await EventPublisher.create_async(redis_manager=self.async_redis_manager)

            # Result logging
            logger.info("✓ Initialized worker services successfully.")
        except Exception as e:
            logger.error(f"Error during worker service initialization: {e}", exc_info=True)
            raise

    @classmethod
    async def create(cls) -> "WorkerServices":
        """Create a new WorkerServices instance and initialize services."""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize_services()
        return cls._instance

    @classmethod
    async def get_instance(cls) -> "WorkerServices":
        """Get the singleton instance of WorkerServices."""
        await cls.create()
        return cls._instance
