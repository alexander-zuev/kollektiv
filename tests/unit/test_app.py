from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.infrastructure.config.settings import Environment
from src.infrastructure.service_container import ServiceContainer


# 1. Service Container Initialization
def test_service_container_initialization():
    container = ServiceContainer()
    with patch.object(container, "initialize_services", return_value=None) as mock_init:
        container.initialize_services()
        mock_init.assert_called_once()

    # Simulate an error during service initialization
    with patch.object(container, "initialize_services", side_effect=Exception("Initialization error")):
        with pytest.raises(Exception, match="Initialization error"):
            container.initialize_services()


# 2. Error Handling in Lifespan
def test_lifespan_error_handling():
    # Mock settings to ensure environment is properly set
    with patch("src.infrastructure.config.settings.settings") as mock_settings:
        mock_settings.environment = Environment.LOCAL
        mock_settings.sentry_dsn = "https://test.sentry.io"

        app = create_app()

        with patch("app.ServiceContainer.initialize_services", side_effect=Exception("Startup error")):
            with pytest.raises(Exception, match="Startup error"):
                with TestClient(app) as client:
                    client.get("/health")
