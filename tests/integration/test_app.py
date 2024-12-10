import pytest
from fastapi.testclient import TestClient

from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.webhook_schemas import FireCrawlEventType
from src.infrastructure.service_container import ServiceContainer


@pytest.mark.integration
class TestAppInitialization:
    """Test suite for application initialization and configuration."""

    def test_app_creates_successfully(self, integration_client: TestClient):
        """Test that the FastAPI application initializes correctly with all required components."""
        # Test app initialization
        assert integration_client.app is not None
        assert hasattr(integration_client.app.state, "container")

        # Test basic app configuration
        assert integration_client.app.title == "Kollektiv API"
        assert integration_client.app.description == "RAG-powered documentation chat application"

    def test_service_container_initialization(self, integration_client: TestClient):
        """Test that the service container initializes with all required services."""
        container = integration_client.app.state.container

        # Verify container type
        assert isinstance(container, ServiceContainer)

        # Verify all required services are initialized and in expected state
        assert container.job_manager is not None
        # Verify job manager is initialized
        assert container.job_manager.jobs_file.exists()

        # Verify FireCrawler initialization
        assert container.firecrawler is not None
        assert container.firecrawler.api_key is not None
        assert container.firecrawler.firecrawl_app is not None

        # Verify content service
        assert container.content_service is not None

    def test_middleware_configuration(self, integration_client: TestClient):
        """Test that all required middleware is properly configured."""
        app = integration_client.app

        # Verify CORS middleware
        assert any(m.cls.__name__ == "CORSMiddleware" for m in app.user_middleware)

        # Verify rate limiting middleware
        assert any(m.cls.__name__ == "HealthCheckRateLimit" for m in app.user_middleware)

    @pytest.mark.parametrize(
        "route_info",
        [
            (Routes.System.HEALTH, "system"),  # health router
            (Routes.System.Webhooks.BASE, "webhooks"),  # webhook router
            (f"{V0_PREFIX}{Routes.V0.CONTENT}", "content"),  # content router
        ],
    )
    def test_required_routers_mounted(self, integration_client: TestClient, route_info: tuple[str, str]):
        """Test that all required routers are mounted."""
        path, tag = route_info
        routes = integration_client.app.routes

        # Check if any route matches the expected path prefix and tag
        matching_routes = [route for route in routes if str(route.path).startswith(path) and tag in route.tags]

        assert matching_routes, f"No routes found matching path '{path}' with tag '{tag}'"


@pytest.mark.integration
class TestEndpointIntegration:
    """Test suite for basic endpoint integration."""

    def test_health_check_endpoint(self, integration_client: TestClient):
        """Test that the health check endpoint returns correct response."""
        response = integration_client.get(Routes.System.HEALTH)
        assert response.status_code == 200
        assert response.json() == {"status": "operational", "message": "All systems operational"}

    @pytest.mark.parametrize(
        "payload",
        [
            {  # Valid payload
                "success": True,
                "event_type": FireCrawlEventType.CRAWL_STARTED.value,
                "crawl_id": "test-crawl-123",
                "data": [{"url": "https://example.com"}],
            },
            {  # Invalid payload - missing required fields
                "success": True,
                "data": [],
            },
        ],
    )
    def test_webhook_endpoint(self, mock_app, mock_webhook_content_service, payload):
        """Test webhook endpoint handles both valid and invalid requests."""
        # Create client for each test to ensure fresh mock state
        client = TestClient(mock_app)
        response = client.post(Routes.System.Webhooks.FIRECRAWL, json=payload)

        if "event_type" in payload:
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            # Verify service was called
            mock_webhook_content_service.handle_event.assert_called_once()
        else:
            assert response.status_code == 400
            assert "Invalid webhook payload" in response.json()["detail"]
            # Verify service was not called
            mock_webhook_content_service.handle_event.assert_not_called()

    def test_sources_endpoint(self, integration_client: TestClient):
        """Test sources endpoint for adding new content sources."""
        test_source = {
            "source_type": "web",
            "config": {
                "url": "https://example.com",
                "max_pages": 1,
            },
        }

        response = integration_client.post(
            f"{V0_PREFIX}{Routes.V0.CONTENT}{Routes.V0.Content.SOURCES}", json=test_source
        )

        assert response.status_code == 201
        data = response.json()

        # Debug print to see actual response structure
        print(f"Response data: {data}")

        assert data["success"] is True
        assert data["message"] == "Source added successfully"
        assert data["data"]["source_type"] == test_source["source_type"]

        # For now, just verify the basic structure until we can see sources_schemas.py
        assert isinstance(data["data"], dict), "Response data should be a dictionary"
