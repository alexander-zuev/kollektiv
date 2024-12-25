from redis.asyncio import Redis

from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.core.content.crawler import FireCrawler
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.reranker import Reranker
from src.core.search.retriever import Retriever
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.chroma_client import ChromaClient
from src.infrastructure.external.redis_client import RedisClient
from src.infrastructure.external.supabase_client import SupabaseClient, supabase_client
from src.infrastructure.rq.rq_manager import RQManager
from src.infrastructure.storage.data_repository import DataRepository
from src.infrastructure.storage.redis_repository import RedisRepository
from src.services.chat_service import ChatService
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class ServiceContainer:
    """Container object for all services that are initialized in the application."""

    def __init__(self) -> None:
        """Initialize container attributes."""
        self.job_manager: JobManager | None = None
        self.firecrawler: FireCrawler | None = None
        self.data_service: DataService | None = None
        self.content_service: ContentService | None = None
        self.repository: DataRepository | None = None
        self.db_client: SupabaseClient | None = None
        self.llm_assistant: ClaudeAssistant | None = None
        self.vector_db: VectorDB | None = None
        self.chat_service: ChatService | None = None
        self.conversation_manager: ConversationManager | None = None
        self.retriever: Retriever | None = None
        self.reranker: Reranker | None = None
        self.redis_client: Redis | None = None
        self.redis_repository: RedisRepository | None = None
        self.embedding_manager: EmbeddingManager | None = None

    async def initialize_services(self) -> None:
        """Initialize all services."""
        try:
            # Database & Repository
            self.db_client = supabase_client
            self.repository = DataRepository(db_client=self.db_client)
            self.data_service = DataService(repository=self.repository)

            # Redis
            self.redis_client = RedisClient().async_client
            if self.redis_client is not None:
                self.redis_repository = RedisRepository(client=self.redis_client)
            else:
                raise ValueError("Redis client is not initialized")

            # RQ
            self.rq_manager = RQManager(redis_client=RedisClient().sync_client)

            # Job & Content Services
            self.job_manager = JobManager(data_service=self.data_service)
            self.firecrawler = FireCrawler()
            self.content_service = ContentService(
                crawler=self.firecrawler,
                job_manager=self.job_manager,
                data_service=self.data_service,
                rq_manager=self.rq_manager,
            )

            # Vector operations
            self.client = await ChromaClient().create_client()
            self.embedding_manager = EmbeddingManager()
            self.vector_db = VectorDB(chroma_client=self.client, embedding_manager=self.embedding_manager)
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

        except Exception as e:
            logger.error(f"Error during service initialization: {e}", exc_info=True)
            raise
