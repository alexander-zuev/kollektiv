from typing import Union

from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.vector_db import VectorDB
from src.infra.data.data_repository import DataRepository
from src.infra.events.event_publisher import EventPublisher
from src.infra.external.chroma_client import ChromaClient
from src.infra.external.redis_client import RedisClient
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.logger import get_logger
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class WorkerServices:
    """Services singleton necessary for RQ worker."""

    _instance: Union["WorkerServices", None] = None

    # def __init__(self) -> None:
    #     logger.info("Initializing services...")

    #     # Initialize sync services
    #     self.chunker = MarkdownChunker()
    #     self.embedding_manager = EmbeddingManager()

    #     # Initialize async services
    #     self.chroma_client = asyncio.run(ChromaClient().create_client())
    #     self.supabase_client = asyncio.run(SupabaseManager.create())

    #     # Initialize dependent services
    #     self.vector_db = VectorDB(chroma_client=self.chroma_client, embedding_manager=self.embedding_manager)
    #     self.repository = DataRepository(db_client=self.supabase_client)
    #     self.data_service = DataService(repository=self.repository)
    #     self.job_manager = JobManager(data_service=self.data_service)

    #     # Add Redis client
    #     self.redis_client = RedisClient().async_client  # For async operations like publish

    #     # Events
    #     self.event_publisher = EventPublisher(redis_client=self.redis_client)

    # @classmethod
    # def get_instance(cls) -> "WorkerServices":
    #     """Get the singleton instance of Services."""
    #     if cls._instance is None:
    #         cls._instance = cls()
    #     return cls._instance

    def __init__(self) -> None:
        logger.info("Initializing worker services...")

        self.job_manager: JobManager | None = None
        self.data_service: DataService | None = None
        self.repository: DataRepository | None = None
        self.supabase_manager: SupabaseManager | None = None
        self.vector_db: VectorDB | None = None
        self.async_redis_client: Redis | None = None
        self.redis_repository: RedisRepository | None = None
        self.embedding_manager: EmbeddingManager | None = None
        self.chroma_client: AsyncClientAPI | None = None
        self.event_publisher: EventPublisher | None = None

    async def initialize_services(self) -> None:
        """Initialize all necesssary worker services."""
        try:
            # Database & Repository
            self.supabase_manager = await SupabaseManager.create()
            self.repository = DataRepository(supabase_manager=self.supabase_manager)
            self.data_service = DataService(repository=self.repository)

            # Redis
            self.async_redis_client = RedisClient().async_client

            # Job & Content Services
            self.job_manager = JobManager(data_service=self.data_service)

            # Vector operations
            self.chroma_client = await ChromaClient().create_client()
            self.embedding_manager = EmbeddingManager()
            self.vector_db = VectorDB(chroma_client=self.chroma_client, embedding_manager=self.embedding_manager)

            # Events
            self.event_publisher = EventPublisher(redis_client=self.async_redis_client)

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
        if cls._instance is None:
            await cls.create()
        return cls._instance
