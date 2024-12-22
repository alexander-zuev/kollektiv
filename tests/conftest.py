import os
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app import create_app
from src.core.chat.llm_assistant import ClaudeAssistant
from src.core.content.crawler import FireCrawler
from src.core.search.vector_db import VectorDB
from src.infrastructure.config.settings import settings
from src.infrastructure.service_container import ServiceContainer
from src.infrastructure.storage.data_repository import DataRepository
from src.infrastructure.storage.redis_repository import RedisRepository
from src.infrastructure.storage.supabase_client import SupabaseClient
from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    Role,
    TextBlock,
)
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
def claude_assistant_with_mock(mock_vector_db: VectorDB) -> ClaudeAssistant:
    """Set up a ClaudeAssistant instance with mocked dependencies."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = Mock()
        mock_client.handle_tool_use = Mock(
            return_value={"role": "user", "content": [{"type": "tool_result", "content": "Tool response"}]}
        )
        mock_anthropic.return_value = mock_client

        assistant = ClaudeAssistant(vector_db=mock_vector_db, retriever=Mock())
        assistant.client = mock_client

        assistant.conversation_history.messages = [ConversationMessage(role="user", content="Initial message")]
        return assistant


@pytest.fixture
def claude_assistant_with_real_db(real_vector_db):
    """Set up a ClaudeAssistant instance with real VectorDB."""
    assistant = ClaudeAssistant(vector_db=real_vector_db)
    return assistant


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption("--run-integration", action="store_true", default=False, help="run integration tests")


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


@pytest.fixture(scope="session")
def mock_app():
    """Session-scoped fixture for the mocked app."""
    test_app = create_app()

    mock_job_manager = MagicMock(spec=JobManager)
    mock_firecrawler = MagicMock(spec=FireCrawler)

    mock_content_service = AsyncMock(spec=ContentService)
    mock_content_service.handle_event = AsyncMock(return_value=None)
    mock_content_service.crawler = mock_firecrawler
    mock_content_service.job_manager = mock_job_manager

    container = MagicMock(spec=ServiceContainer)
    container.job_manager = mock_job_manager
    container.firecrawler = mock_firecrawler
    container.content_service = mock_content_service

    test_app.state.container = container
    return test_app


@pytest.fixture
def integration_app():
    """Integration test app with mocked external services."""
    test_app = create_app()
    container = ServiceContainer()

    # Create mock FireCrawler with necessary attributes
    mock_firecrawler = MagicMock(spec=FireCrawler)
    mock_firecrawler.api_key = "test-key"  # Set the api_key attribute
    mock_firecrawler.firecrawl_app = mock_firecrawler.initialize_firecrawl()

    # Mock DataService
    mock_data_service = MagicMock(spec=DataService)

    # Mock specific services while keeping container structure
    container.job_manager = JobManager(data_service=mock_data_service)
    container.firecrawler = mock_firecrawler
    container.content_service = ContentService(
        job_manager=container.job_manager, crawler=container.firecrawler, data_service=mock_data_service
    )

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
    client = SupabaseClient(url=settings.supabase_url, key=settings.supabase_service_key, schema="public")
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
def mock_redis():
    """Fast fake Redis for unit tests."""
    return FakeRedis()


@pytest.fixture
def redis_repository(mock_redis):
    """Repository with fake Redis for unit tests."""
    return RedisRepository(mock_redis)


@pytest.fixture(scope="session")
async def redis_test_client():
    """Real Redis client for integration tests."""
    redis = Redis(host=settings.redis_host, port=settings.redis_port)
    try:
        await redis.ping()
        await redis.flushall()  # Clean the Redis instance before tests
    except Exception as e:
        raise RuntimeError(
            "Redis server is required for integration tests.\n"
            "Start it with: docker run -d -p 6379:6379 redis:7-alpine"
        ) from e

    yield redis
    await redis.flushall()  # Clean after tests
    await redis.close()


@pytest.fixture
async def redis_integration_repository(redis_test_client):
    """Repository with real Redis for integration tests."""
    return RedisRepository(redis_test_client)


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
