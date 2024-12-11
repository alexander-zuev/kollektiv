import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from pathlib import Path
from typing import Generic, TypeVar

import numpy as np
import pytest
from chromadb.api.types import Document, Documents, Embedding, EmbeddingFunction
from fastapi.testclient import TestClient

# Create log directory
TEST_LOG_DIR = Path("/tmp/kollektiv_test_logs")
TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create settings mock before any imports
settings_mock = MagicMock(
    ENVIRONMENT="test",
    FIRECRAWL_API_KEY="test-key",
    ANTHROPIC_API_KEY="test-anthropic-key",
    OPENAI_API_KEY="test-openai-key",
    COHERE_API_KEY="test-cohere-key",
    SUPABASE_URL="https://test-supabase-url",
    SUPABASE_SERVICE_KEY="test-supabase-key",
    LOGFIRE_TOKEN="test-logfire-token",
    REDIS_URL="redis://localhost:6379",
    CORS_ORIGINS="*",
    ALLOWED_HOSTS="*",
    LOG_LEVEL="DEBUG",
    SENTRY_DSN="",
    LOG_DIR=str(TEST_LOG_DIR)
)

# Mock modules before importing app
sys.modules['logfire'] = MagicMock()
sys.modules['src.infrastructure.config.settings'] = MagicMock(settings=settings_mock)
sys.modules['src.infrastructure.common.logger'] = MagicMock()

from app import create_app
from src.core.chat.claude_assistant import ClaudeAssistant
from src.models.chat_models import ConversationMessage
from src.core.content.crawler import FireCrawler
from src.core.search.vector_db import VectorDB
from src.infrastructure.service_container import ServiceContainer
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager

T = TypeVar('T')

class MockEmbeddingFunction(EmbeddingFunction[T]):
    def __call__(self, input: Document | Documents) -> list[Embedding]:
        mock_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        return [mock_embedding] if isinstance(input, str) else [mock_embedding for _ in input]


@pytest.fixture
def mock_openai_embeddings(monkeypatch):
    mock_func = MockEmbeddingFunction()
    monkeypatch.setattr("chromadb.utils.embedding_functions.OpenAIEmbeddingFunction", lambda **kwargs: mock_func)
    return mock_func


@pytest.fixture(autouse=True)
def mock_environment_variables():
    original_env = dict(os.environ)

    test_env = os.getenv("ENVIRONMENT", "local")

    env_vars = {
        "ENVIRONMENT": test_env,
        "FIRECRAWL_API_KEY": "test-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "OPENAI_API_KEY": "test-openai-key",
        "COHERE_API_KEY": "test-cohere-key",
        "SUPABASE_URL": "https://test-supabase-url",
        "SUPABASE_SERVICE_KEY": "test-supabase-key",
        "LOGFIRE_TOKEN": "test-logfire-token",
        "REDIS_URL": "redis://localhost:6379",
        "CORS_ORIGINS": "*",
        "ALLOWED_HOSTS": "*",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
        "SENTRY_DSN": "",
        "FIRECRAWL_API_KEY": "test-key",
    }

    if test_env == "staging":
        env_vars.update(
            {
                "BASE_URL": "http://mock-api:8000",
            }
        )

    with patch.dict(os.environ, env_vars, clear=True):
        yield

    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_vector_db():
    return MagicMock(spec=VectorDB)


@pytest.fixture
def real_vector_db():
    return VectorDB()


@pytest.fixture
def claude_assistant_with_mock(mock_vector_db: VectorDB) -> ClaudeAssistant:
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = Mock()
        mock_client.handle_tool_use = Mock(
            return_value={"role": "user", "content": [{"type": "tool_result", "content": "Tool response"}]}
        )
        mock_anthropic.return_value = mock_client

        assistant = ClaudeAssistant(vector_db=mock_vector_db)
        assistant.client = mock_client

        assistant.conversation_history.messages = [ConversationMessage(role="user", content="Initial message")]
        return assistant


@pytest.fixture
def claude_assistant_with_real_db(real_vector_db):
    assistant = ClaudeAssistant(vector_db=real_vector_db)
    return assistant


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False, help="run integration tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


@pytest.fixture(scope="session")
def mock_app():
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
    test_app = create_app()
    container = ServiceContainer()

    mock_firecrawler = MagicMock(spec=FireCrawler)
    mock_firecrawler.api_key = "test-key"
    mock_firecrawler.firecrawl_app = mock_firecrawler.initialize_firecrawl()

    mock_data_service = MagicMock(spec=DataService)

    container.job_manager = JobManager(data_service=mock_data_service)
    container.firecrawler = mock_firecrawler
    container.content_service = ContentService(
        job_manager=container.job_manager, crawler=container.firecrawler, data_service=mock_data_service
    )

    test_app.state.container = container
    return test_app


@pytest.fixture(scope="function")
def mock_client(mock_app):
    return TestClient(mock_app, raise_server_exceptions=True)


@pytest.fixture
def integration_client(integration_app):
    return TestClient(integration_app, raise_server_exceptions=True)


@pytest.fixture
def mock_content_service():
    with patch("src.api.v0.endpoints.webhooks.ContentServiceDep", new_callable=MagicMock) as mock_service:
        yield mock_service


@pytest.fixture
def mock_webhook_content_service(mock_app):
    mock_job_manager = MagicMock(spec=JobManager)
    mock_firecrawler = MagicMock(spec=FireCrawler)

    mock_service = AsyncMock(spec=ContentService)
    mock_service.handle_event = AsyncMock(return_value=None)
    mock_service.crawler = mock_firecrawler
    mock_service.job_manager = mock_job_manager

    with patch("src.api.v0.endpoints.webhooks.ContentServiceDep", return_value=mock_service):
        mock_app.state.container.content_service = mock_service
        yield mock_service
