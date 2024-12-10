import os
import sys
from pathlib import Path

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

from typing import Any, Generic, List, Optional, TypeVar
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
import pytest_asyncio
from anthropic.types import (
    MessageStartEvent,
    MessageDeltaEvent,
    MessageStopEvent,
)
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction
from fastapi.testclient import TestClient

from src.core.search.vector_db import VectorDB
from src.infrastructure.config.settings import Environment, settings
from tests.test_settings import TestSettings

# Create comprehensive settings mock before any imports
settings_mock = Mock()
settings_mock.anthropic_api_key = "test-key"
settings_mock.main_model = "claude-3-5-sonnet-20241022"
settings_mock.evaluator_model_name = "gpt-4o-mini"
settings_mock.embedding_model = "text-embedding-3-small"
settings_mock.environment = "local"
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

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_weave():
    """Mock weave for testing."""
    mock = Mock()
    mock.init = Mock()
    mock.log = Mock()
    mock.__len__ = Mock(return_value=0)  # Add this line to handle len() calls

    with patch.dict("sys.modules", {"weave": mock}):
        yield mock

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
    test_env = {
        "ENVIRONMENT": Environment.LOCAL.value,
        "FIRECRAWL_API_KEY": "test-key",
        "ANTHROPIC_API_KEY": "test-key",
        "OPENAI_API_KEY": "test-key",
        "COHERE_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "LOGFIRE_TOKEN": "test-key",
        "REDIS_URL": "redis://localhost:6379",
        "LOG_LEVEL": "DEBUG"
    }

    with patch.dict(os.environ, test_env, clear=True):
        test_settings = TestSettings()
        with patch("src.infrastructure.config.settings.settings", test_settings):
            yield test_settings


@pytest.fixture
async def mock_vector_db():
    """Create a mock vector database."""
    class MockVectorDB(VectorDB):
        async def search(self, query: str, limit: int = 5) -> List[Document]:
            return []

        async def add_documents(self, documents: Documents) -> None:
            pass

        async def delete_documents(self, ids: List[str]) -> None:
            pass

    return MockVectorDB()


@pytest.fixture
def real_vector_db():
    """Create a real VectorDB instance for testing."""
    return VectorDB()


@pytest_asyncio.fixture
async def claude_assistant_with_mock(mock_vector_db: VectorDB):
    """Create a ClaudeAssistant instance with mocked dependencies."""
    # Create test events for streaming with proper schema
    events = [
        MessageStartEvent(
            type="message_start",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-3-sonnet-20240229",
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            }
        ),
        MessageDeltaEvent(
            type="message_delta",
            delta={
                "type": "text",
                "text": "Test response",
            },
            usage={
                "input_tokens": 10,
                "output_tokens": 5
            }
        ),
        MessageStopEvent(
            type="message_stop",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Test response"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    ]

    # Create async generator for streaming
    async def mock_stream():
        for event in events:
            yield event

    # Mock the Anthropic client
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=mock_stream)

    # Initialize the assistant with mocks
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        from src.core.chat.claude_assistant import ClaudeAssistant
        assistant = ClaudeAssistant(
            vector_db=mock_vector_db,
            api_key="test-key",
            model="claude-3-sonnet-20240229",
            max_tokens=4096,
        )
        # Set up the mocked client
        assistant.client = mock_client
        yield assistant


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
