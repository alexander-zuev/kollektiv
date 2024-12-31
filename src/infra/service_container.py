from __future__ import annotations

from redis.asyncio import Redis

from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.core.content.crawler import FireCrawler
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.reranker import Reranker
from src.core.search.retriever import Retriever
from src.core.search.vector_db import VectorDatabase
from src.infra.data.data_repository import DataRepository
from src.infra.data.redis_repository import RedisRepository
from src.infra.events.event_consumer import EventConsumer
from src.infra.events.event_publisher import EventPublisher
from src.infra.external.chroma_manager import ChromaManager
from src.infra.external.redis_manager import RedisManager
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.logger import get_logger
from src.infra.misc.ngrok_service import NgrokService
from src.services.chat_service import ChatService
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class ServiceContainer:
    """Container object for all services that are initialized in the application."""

    def __init__(self) -> None:
        """Initialize Kollektiv container attributes."""
        self.job_manager: JobManager | None = None
        self.firecrawler: FireCrawler | None = None
        self.data_service: DataService | None = None
        self.content_service: ContentService | None = None
        self.repository: DataRepository | None = None
        self.supabase_manager: SupabaseManager | None = None
        self.llm_assistant: ClaudeAssistant | None = None
        self.vector_db: VectorDatabase | None = None
        self.chat_service: ChatService | None = None
        self.conversation_manager: ConversationManager | None = None
        self.retriever: Retriever | None = None
        self.reranker: Reranker | None = None
        self.async_redis_client: Redis | None = None
        self.redis_repository: RedisRepository | None = None
        self.embedding_manager: EmbeddingManager | None = None
        self.ngrok_service: NgrokService | None = None
        self.chroma_manager: ChromaManager | None = None
        self.event_publisher: EventPublisher | None = None
        self.event_consumer: EventConsumer | None = None

    async def initialize_services(self) -> None:
        """Initialize all services."""
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
            self.firecrawler = FireCrawler()
            self.content_service = ContentService(
                crawler=self.firecrawler,
                job_manager=self.job_manager,
                data_service=self.data_service,
            )

            # Vector operations
            self.chroma_manager = await ChromaManager.create_async()
            self.embedding_manager = EmbeddingManager()
            self.vector_db = VectorDatabase(
                chroma_manager=self.chroma_manager,
                embedding_manager=self.embedding_manager,
                data_service=self.data_service,
            )
            self.reranker = Reranker()
            self.retriever = Retriever(vector_db=self.vector_db, reranker=self.reranker)

            # Chat Services
            self.claude_assistant = ClaudeAssistant(vector_db=self.vector_db, retriever=self.retriever)
            self.conversation_manager = ConversationManager(
                redis_repository=self.redis_repository, data_service=self.data_service
            )
            self.chat_service = ChatService(
                claude_assistant=self.claude_assistant,
                data_service=self.data_service,
                conversation_manager=self.conversation_manager,
            )
            self.ngrok_service = await NgrokService.create()

            # Events
            self.event_publisher = await EventPublisher.create_async(redis_manager=self.async_redis_manager)
            self.event_consumer = await EventConsumer.create_async(
                redis_manager=self.async_redis_manager, content_service=self.content_service
            )
            await self.event_consumer.start()

            # Log the successful initialization
            logger.info("✓ Initialized services successfully.")
        except Exception as e:
            logger.error(f"Error during service initialization: {e}", exc_info=True)
            raise

    @classmethod
    async def create(cls) -> ServiceContainer:
        """Create a new ServiceContainer instance and initialize services."""
        container = cls()
        await container.initialize_services()
        return container

    async def shutdown_services(self) -> None:
        """Shutdown all services."""
        try:
            if self.ngrok_service is not None:
                await self.ngrok_service.stop_tunnel()

            if self.event_consumer is not None:
                await self.event_consumer.stop()

        except Exception as e:
            logger.error(f"Error during service shutdown: {e}", exc_info=True)
