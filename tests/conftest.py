import os
import subprocess
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from anthropic.types import (
    ContentBlockStartEvent,
    RawContentBlockDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextDelta,
)
from chromadb import AsyncClientAPI
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from src.app import create_app
from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.core.chat.prompt_manager import PromptManager, SystemPrompt
from src.core.chat.tool_manager import Tool, ToolManager
from src.core.content.crawler import FireCrawler
from src.core.search.embedding_manager import EmbeddingManager
from src.core.search.reranker import Reranker
from src.core.search.retriever import Retriever
from src.core.search.vector_db import VectorDB
from src.infra.data.data_repository import DataRepository
from src.infra.data.redis_repository import RedisRepository
from src.infra.external.chroma_manager import ChromaManager
from src.infra.external.redis_manager import RedisManager
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.rq.rq_manager import RQManager
from src.infra.service_container import ServiceContainer
from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    Role,
    TextBlock,
)
from src.services.chat_service import ChatService
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager


class MockEmbeddingFunction(EmbeddingFunction):
    """Mock embedding function that follows ChromaDB's interface."""

    def __call__(self, input: Document | Documents) -> list[Embedding]:
        """Return mock embeddings that match ChromaDB's expected types."""
        mock_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        if isinstance(input, str):
            return [mock_embedding]
        return [mock_embedding for _ in input]


@pytest.fixture
def mock_openai_embeddings(monkeypatch):
    """Mock OpenAI embeddings for unit tests."""
    mock_func = MockEmbeddingFunction()
    monkeypatch.setattr("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction", lambda **kwargs: mock_func)
    return mock_func


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Set required environment variables for tests."""
    # Store original environment
    original_env = dict(os.environ)

    # Get environment from actual env var, default to LOCAL
    test_env = os.getenv("ENVIRONMENT", "local")

    env_vars = {
        "ENVIRONMENT": test_env,
        "WANDB_MODE": "disabled",
        "WEAVE_PROJECT_NAME": "",
        "ANTHROPIC_API_KEY": "test-key",
        "COHERE_API_KEY": "test-key",
        "OPENAI_API_KEY": "test-key",
        "FIRECRAWL_API_KEY": "test-key",
    }

    # If we're in staging, add required staging vars
    if test_env == "staging":
        env_vars.update(
            {
                "BASE_URL": "http://mock-api:8000",  # Mock staging URL
            }
        )

    with patch.dict(os.environ, env_vars, clear=True):
        yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_vector_db():
    """Create a mock object for VectorDB."""
    return MagicMock(spec=VectorDB)


@pytest.fixture
def real_vector_db():
    """Create a real VectorDB instance for testing."""
    return VectorDB()


@pytest.fixture
async def mock_anthropic_client():
    """Create a mock Anthropic client with common responses."""
    # Create a Messages class mock first
    mock_messages = AsyncMock()

    # Create a mock message with proper structure
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(type="text", text="Test response", model_dump=lambda: {"type": "text", "text": "Test response"})
    ]
    mock_message.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_message.stop_reason = "end_turn"
    mock_message.model_dump = MagicMock(
        return_value={"content": [{"type": "text", "text": "Test response"}], "role": "assistant"}
    )

    # Setup stream response with proper event types
    mock_stream = AsyncMock()
    mock_stream.get_final_message.return_value = mock_message

    # Setup async context manager for streaming
    async def mock_stream_context():
        mock_stream_instance = AsyncMock()
        mock_stream_instance.get_final_message.return_value = mock_message
        yield RawMessageStartEvent(
            type="message_start",
            message={
                "id": "test-message-id",
                "content": [],
                "model": "test-model",
                "role": "assistant",
                "type": "message",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        )
        yield RawContentBlockDeltaEvent(
            type="content_block_delta", delta=TextDelta(type="text_delta", text="Test response"), index=0
        )
        yield RawMessageStopEvent(type="message_stop", message=mock_message.model_dump())

    # Attach the mocked methods to messages
    mock_messages.create = AsyncMock(return_value=mock_message)
    mock_messages.stream = AsyncMock(__aenter__=mock_stream_context)

    # Now create the client with the messages attribute pre-configured
    mock_client = AsyncMock()
    mock_client.messages = mock_messages

    return mock_client


@pytest.fixture
async def mock_retriever():
    """Create a mock Retriever with predefined responses."""
    mock_retriever = AsyncMock(spec=Retriever)
    mock_retriever.retrieve = AsyncMock(return_value=["Test document 1", "Test document 2"])
    mock_retriever.use_rag_search = AsyncMock(return_value=["Test search result"])
    return mock_retriever


@pytest.fixture
def mock_tool_manager():
    """Create a mock ToolManager with predefined tools."""
    mock_manager = Mock(spec=ToolManager)
    mock_manager.get_all_tools.return_value = [
        Tool(
            name="rag_search",
            description="Search using RAG",
            input_schema={"type": "object", "properties": {"important_context": {"type": "string"}}},
        ).with_cache()
    ]
    return mock_manager


@pytest.fixture
def mock_prompt_manager():
    """Create a mock PromptManager with predefined prompts."""
    mock_manager = Mock(spec=PromptManager)
    mock_manager.get_system_prompt.return_value = SystemPrompt(text="Test system prompt")
    return mock_manager


@pytest.fixture
async def claude_assistant_with_mocks(
    mock_vector_db,
    mock_anthropic_client,
    mock_retriever,
    mock_tool_manager,
    mock_prompt_manager,
):
    """Create a ClaudeAssistant instance with all dependencies mocked."""
    with patch("anthropic.AsyncAnthropic", return_value=mock_anthropic_client) as mock_anthropic:
        assistant = ClaudeAssistant(
            vector_db=mock_vector_db,
            retriever=mock_retriever,
            api_key="test-key",
            model_name="test-model",
        )
        assistant.tool_manager = mock_tool_manager
        assistant.prompt_manager = mock_prompt_manager
        return assistant


@pytest.fixture
def streaming_events():
    """Create sample streaming events for testing."""
    return {
        "message_start": RawMessageStartEvent(
            type="message_start",
            message={
                "id": "test-message-id",
                "content": [],
                "model": "test-model",
                "role": "assistant",
                "type": "message",
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        ),
        "content_block_start": ContentBlockStartEvent(
            type="content_block_start",
            content_block=Mock(type="text", id="test-id"),
            index=0,
        ),
        "content_block_delta": RawContentBlockDeltaEvent(
            type="content_block_delta",
            delta=TextDelta(type="text_delta", text="test"),
            index=0,
        ),
        "message_stop": RawMessageStopEvent(type="message_stop", message={}),
    }


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption("--run-integration", action="store_true", default=False, help="run integration tests")


def pytest_configure(config):
    """Configure custom markers and start containers for integration tests."""
    # Add test markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")

    # Start containers for integration tests
    if config.getoption("--run-integration"):
        subprocess.run(
            ["docker", "compose", "--env-file", "config/.env", "-f", "scripts/docker/compose.yaml", "up", "-d"],
            check=True,
        )


def pytest_unconfigure(config):
    """Cleanup containers after tests."""
    if config.getoption("--run-integration"):
        subprocess.run(
            ["docker", "compose", "--env-file", "config/.env", "-f", "scripts/docker/compose.yaml", "down"], check=True
        )


@pytest.fixture(scope="function")
async def mock_app():
    """Function-scoped fixture for fully mocked app."""
    test_app = create_app()

    # Create container with all required mocks
    container = MagicMock(spec=ServiceContainer)

    # 1. Database & Repository Layer
    container.db_client = MagicMock(spec=SupabaseManager)
    container.repository = MagicMock(spec=DataRepository)
    container.data_service = MagicMock(spec=DataService)

    # 2. Redis Layer
    container.redis_client = MagicMock(spec=Redis)
    container.redis_repository = MagicMock(spec=RedisRepository)
    container.rq_manager = MagicMock(spec=RQManager)

    # 3. Job & Content Layer
    container.job_manager = MagicMock(spec=JobManager)
    container.firecrawler = MagicMock(spec=FireCrawler)
    container.content_service = AsyncMock(spec=ContentService)

    # 4. Vector & Search Layer
    container.vector_db = MagicMock(spec=VectorDB)
    container.embedding_manager = MagicMock(spec=EmbeddingManager)
    container.retriever = MagicMock(spec=Retriever)
    container.reranker = MagicMock(spec=Reranker)

    # 5. Chat Layer
    container.claude_assistant = MagicMock(spec=ClaudeAssistant)
    container.conversation_manager = MagicMock(spec=ConversationManager)
    container.chat_service = MagicMock(spec=ChatService)

    test_app.state.container = container
    return test_app


@pytest.fixture
async def integration_app():
    """Integration test app with minimal required mocking."""
    # Run integration tests in STAGING to avoid ngrok
    test_app = create_app()
    container = await ServiceContainer.create()

    # Mock only external services that can't be run in tests
    container.firecrawler = MagicMock(spec=FireCrawler)
    container.firecrawler.api_key = "test-key"
    container.firecrawler.firecrawl_app = MagicMock()

    # Mock expensive services
    container.claude_assistant = MagicMock(spec=ClaudeAssistant)

    test_app.state.container = container
    return test_app


@pytest.fixture(scope="function")
def mock_client(mock_app):
    """Function-scoped fixture for the test client."""
    return TestClient(mock_app, raise_server_exceptions=True)


@pytest.fixture
def integration_client(integration_app):
    """TestClient with real services for integration tests."""
    return TestClient(integration_app, raise_server_exceptions=True)


@pytest.fixture
def mock_content_service():
    """Fixture to mock the content service dependency."""
    with patch("src.api.v0.endpoints.webhooks.ContentServiceDep", new_callable=MagicMock) as mock_service:
        yield mock_service


@pytest.fixture
def mock_webhook_content_service(mock_app):
    """Fixture specifically for webhook testing with async support."""
    mock_job_manager = MagicMock(spec=JobManager)
    mock_firecrawler = MagicMock(spec=FireCrawler)

    mock_service = AsyncMock(spec=ContentService)
    mock_service.handle_event = AsyncMock(return_value=None)
    mock_service.crawler = mock_firecrawler
    mock_service.job_manager = mock_job_manager

    with patch("src.api.v0.endpoints.webhooks.ContentServiceDep", return_value=mock_service):
        mock_app.state.container.content_service = mock_service
        yield mock_service


@pytest.fixture
async def db_client():
    """Create a test database client."""
    manager = SupabaseManager.create_async()
    client = await manager.get_async_client()
    yield client
    await client.close()


@pytest.fixture
async def data_repository(db_client):
    """Create a test data repository."""
    return DataRepository(db_client=db_client)


@pytest.fixture
async def data_service(data_repository):
    """Create a test data service."""
    return DataService(repository=data_repository)


# Redis-related fixtures
@pytest.fixture
def mock_sync_redis():
    """Mock for synchronous Redis client."""
    mock_client = MagicMock(spec=SyncRedis)
    mock_client.ping.return_value = True
    return mock_client


@pytest.fixture
def mock_async_redis():
    """Mock for asynchronous Redis client."""
    mock_client = AsyncMock(spec=AsyncRedis)
    # Basic Redis operations
    mock_client.ping = AsyncMock(return_value=True)

    # Setup pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, True])
    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock()
    mock_client.pipeline = AsyncMock(return_value=mock_pipeline)

    # Repository operations
    mock_client.set = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.rpush = AsyncMock()
    mock_client.lrange = AsyncMock(return_value=[])
    mock_client.delete = AsyncMock()
    mock_client.lpop = AsyncMock()
    mock_client.rpop = AsyncMock()
    return mock_client


@pytest.fixture
def redis_repository(mock_async_redis):
    """Repository with mocked Redis for unit tests."""
    manager = RedisManager()
    manager._async_client = mock_async_redis
    return RedisRepository(manager=manager)


@pytest.fixture(scope="function")
async def redis_integration_manager():
    """Real RedisManager for integration tests."""
    manager = await RedisManager.create_async()
    if manager._async_client:
        await manager._async_client.flushall()  # Clean before test
    yield manager
    if manager._async_client:
        await manager._async_client.flushall()  # Clean after test


@pytest.fixture
async def redis_integration_repository(redis_integration_manager):
    """Repository with real Redis for integration tests."""
    return RedisRepository(manager=redis_integration_manager)


# Chat & Conversation Fixtures
@pytest.fixture
def sample_uuid():
    """Sample UUID for testing."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_message(sample_uuid):
    """Sample message for testing."""
    return ConversationMessage(message_id=sample_uuid, role=Role.USER, content=[TextBlock(text="Test message")])


@pytest.fixture
def sample_conversation(sample_uuid, sample_message):
    """Sample conversation for testing."""
    return ConversationHistory(conversation_id=sample_uuid, messages=[sample_message])


@pytest.fixture
def mock_chroma_client():
    """Mock for ChromaDB async client."""
    mock_client = AsyncMock(spec=AsyncClientAPI)
    mock_client.heartbeat = AsyncMock()
    return mock_client


@pytest.fixture
def mock_chroma_manager():
    """Mock for ChromaManager."""
    mock_manager = AsyncMock(spec=ChromaManager)
    mock_manager._client = None
    return mock_manager


@pytest.fixture
def mock_redis_pipeline():
    """Mock for Redis pipeline."""
    mock_pipeline = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, True])  # Simulate successful execution
    return mock_pipeline


@pytest.fixture
def mock_redis_with_pipeline(mock_redis, mock_redis_pipeline):
    """Mock Redis with pipeline support."""
    mock_redis.pipeline = AsyncMock(return_value=mock_redis_pipeline)
    return mock_redis
