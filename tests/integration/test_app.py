import pytest
from fastapi.testclient import TestClient

from src.infra.service_container import ServiceContainer


@pytest.mark.integration
class TestAppInitialization:
    """Test suite for application initialization and configuration."""

    def test_app_creates_successfully(self, integration_client: TestClient):
        """Test that the FastAPI application initializes correctly."""
        assert integration_client.app is not None
        assert hasattr(integration_client.app.state, "container")
        assert integration_client.app.title == "Kollektiv API"

    def test_service_container_initialization(self, integration_client: TestClient):
        """Test that the service container initializes with all required services."""
        container = integration_client.app.state.container
        assert isinstance(container, ServiceContainer)

        # Core services that must be present
        assert container.job_manager is not None
        assert container.content_service is not None
        assert container.data_service is not None

        # Redis services
        assert container.async_redis_manager is not None
        assert container.redis_repository is not None
        assert container.event_publisher is not None

        # Vector operations
        assert container.chroma_manager is not None
        assert container.embedding_manager is not None
        assert container.vector_db is not None
        assert container.retriever is not None
        assert container.reranker is not None

        # Chat services
        assert container.claude_assistant is not None
        assert container.conversation_manager is not None
        assert container.chat_service is not None

    def test_middleware_setup(self, integration_client: TestClient):
        """Test middleware configuration."""
        app = integration_client.app
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]

        assert "CORSMiddleware" in middleware_classes
        assert "HealthCheckRateLimit" in middleware_classes
