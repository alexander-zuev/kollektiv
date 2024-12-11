import os
import sys
from pathlib import Path
from typing import Any, Generic, List, Optional, TypeVar

# Set test environment variables before any imports
os.environ.update({
    "ENVIRONMENT": "local",
    "FIRECRAWL_API_KEY": "test-key",
    "ANTHROPIC_API_KEY": "test-key",
    "OPENAI_API_KEY": "test-key",
    "COHERE_API_KEY": "test-key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-key",
    "LOGFIRE_TOKEN": "test-key",
    "REDIS_URL": "redis://localhost:6379",
    "LOG_LEVEL": "DEBUG"
})

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
import pytest_asyncio
from anthropic import AsyncAnthropic, APIStatusError
from anthropic.types import (
    Message,
    ContentBlock,
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    MessageStartEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    TextBlock,
    TextDelta,
    Usage,
)
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction
from fastapi.testclient import TestClient

from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.search.vector_db import ResultRetriever, VectorDB, Reranker
from src.infrastructure.config.settings import Environment, settings
from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    MessageContent,
    Role,
    StandardEvent,
    StandardEventType,
    TextBlock as ChatTextBlock,
)
from tests.test_settings import TestSettings

# Create comprehensive settings mock before any imports
settings_mock = Mock()
settings_mock.anthropic_api_key = "test-key"
settings_mock.main_model = "claude-3-5-sonnet-20241022"
settings_mock.evaluator_model_name = "gpt-4o-mini"
settings_mock.embedding_model = "text-embedding-3-small"
settings_mock.environment = Environment.LOCAL  # Use Environment enum
settings_mock.project_name = "kollektiv"
settings_mock.log_level = "debug"
settings_mock.api_host = "127.0.0.1"
settings_mock.api_port = 8000
settings_mock.log_dir = str(Path(__file__).parent.parent / "logs")
settings_mock.debug = True
settings_mock.cors_origins = ["http://localhost:3000"]
settings_mock.redis_url = "redis://localhost:6379"
settings_mock.supabase_url = "https://test.supabase.co"
settings_mock.supabase_service_key = "test-supabase-key"
settings_mock.logfire_token = "test-logfire-token"
settings_mock.sentry_dsn = None

# Create the settings module mock
settings_module = Mock()
settings_module.settings = settings_mock
sys.modules["src.infrastructure.config.settings"] = settings_module

# Set environment variables before any imports
os.environ.update({
    "ENVIRONMENT": "test",
    "WANDB_MODE": "disabled",
    "WEAVE_PROJECT_NAME": "",
    "ANTHROPIC_API_KEY": "test-key",
    "COHERE_API_KEY": "test-key",
    "OPENAI_API_KEY": "test-key",
    "FIRECRAWL_API_KEY": "test-key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-supabase-key",
    "LOGFIRE_TOKEN": "test-logfire-token",
    "REDIS_URL": "redis://localhost:6379",
    "LOG_LEVEL": "DEBUG",
    "API_HOST": "http://localhost:8000",
    "CORS_ORIGINS": "http://localhost:3000",
})

# Create logs directory if it doesn't exist
Path(settings_mock.log_dir).mkdir(parents=True, exist_ok=True)

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_weave():
    """Mock weave initialization."""
    with patch("wandb.init") as mock_init, \
         patch("wandb.login") as mock_login, \
         patch("wandb.sdk.lib.disabled") as mock_disabled:
        mock_disabled.return_value = True  # Disable wandb completely
        mock_init.return_value = MagicMock()
        mock_login.return_value = True
        yield mock_init

# Import app modules after environment setup
from app import create_app
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.content.crawler import FireCrawler
from src.core.search.vector_db import VectorDB
from src.infrastructure.service_container import ServiceContainer
from src.models.chat_models import (
    ConversationMessage,
    MessageContent,
    TextBlock,
    StandardEvent,
    StandardEventType,
)
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager


T = TypeVar('T')

class MockEmbeddingFunction(EmbeddingFunction[T]):
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
def mock_settings():
    """Mock settings for testing."""
    with patch("src.infrastructure.config.settings.settings") as mock_settings:
        mock_settings.environment = Environment.LOCAL
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.openai_api_key = "test-key"
        mock_settings.cohere_api_key = "test-key"
        mock_settings.firecrawl_api_key = "test-key"
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test-key"
        mock_settings.logfire_token = "test-key"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings.log_level = "DEBUG"
        mock_settings.main_model = "claude-3-sonnet-20240229"
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.cors_origins = ["http://localhost:3000"]
        mock_settings.debug = True
        yield mock_settings


@pytest.fixture
def mock_vector_db():
    """Create a mock VectorDB instance."""
    mock_reranker = MagicMock(spec=Reranker)
    mock_reranker.rerank = AsyncMock(return_value=[{"text": "Mock reranked result", "score": 0.95}])

    mock_retriever = MagicMock(spec=ResultRetriever)
    mock_retriever.collection_name = "test_collection"
    mock_retriever.embedding_function = MockEmbeddingFunction()
    mock_retriever.reranker = mock_reranker
    mock_retriever.get_results = AsyncMock(return_value=[{"text": "Mock result", "score": 0.9}])
    # Initialize with required arguments
    mock_retriever.__init__ = AsyncMock(return_value=None)
    mock_retriever.collection_name = "test_collection"
    mock_retriever.embedding_function = MockEmbeddingFunction()

    mock_db = MagicMock(spec=VectorDB)
    mock_db.collection_name = "test_collection"
    mock_db.reranker = mock_reranker
    mock_db.result_retriever = mock_retriever
    mock_db.search = AsyncMock(return_value=[{"text": "Mock search result", "score": 0.9}])
    mock_db.add_documents = AsyncMock(return_value=["doc_id_1"])
    mock_db.delete_documents = AsyncMock(return_value=True)

    return mock_db


@pytest.fixture
def real_vector_db():
    """Create a real VectorDB instance for testing."""
    return VectorDB()


@pytest_asyncio.fixture
async def claude_assistant_with_mock():
    """Create a ClaudeAssistant instance with mocked client."""
    # Mock Anthropic client
    mock_client = AsyncMock(spec=AsyncAnthropic)

    # Mock ResultRetriever
    mock_retriever = AsyncMock(spec=ResultRetriever)
    mock_retriever.search.return_value = [{"text": "Mock search result"}]

    # Create assistant with mocks
    assistant = ClaudeAssistant()
    assistant.client = mock_client
    assistant._result_retriever = mock_retriever

    # Set up streaming mock
    class AsyncStreamContextManager:
        """Mock async context manager for streaming."""
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def __aiter__(self):
            """Generate mock streaming events."""
            # Message start
            yield MessageStartEvent(
                type="message_start",
                message=Message(
                    id="msg_123",
                    type="message",
                    role="assistant",
                    content=[],
                    model="claude-3-opus-20240229",
                    usage=Usage(
                        input_tokens=10,
                        output_tokens=20,
                        multiplier=1.0
                    )
                )
            )

            # Content block with text
            yield ContentBlockDeltaEvent(
                type="content_block_delta",
                delta=TextDelta(type="text_delta", text="Hello"),
                index=0
            )

            # Message stop
            yield MessageStopEvent(
                type="message_stop",
                message=Message(
                    id="msg_123",
                    type="message",
                    role="assistant",
                    content=[{"type": "text", "text": "Hello"}],
                    model="claude-3-opus-20240229",
                    stop_reason="end_turn",
                    usage=Usage(
                        input_tokens=10,
                        output_tokens=20,
                        multiplier=1.0
                    )
                )
            )

    # Configure streaming mock
    mock_stream = AsyncStreamContextManager()
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    yield assistant


@pytest.fixture
async def claude_assistant_with_real_db():
    """Create a Claude Assistant instance with real VectorDB."""
    # Create real VectorDB instance
    real_vector_db = VectorDB(
        reranker=Reranker(),
        result_retriever=ResultRetriever(
            collection_name="test_collection",
            embedding_function=MagicMock()
        ),
        collection_name="test_collection"
    )

    # Create test assistant
    assistant = ClaudeAssistant(
        client=AsyncMock(),
        model_name="claude-3-sonnet-20240229",
        max_tokens=1000,
        vector_db=real_vector_db
    )

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
