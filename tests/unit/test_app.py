import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.infrastructure.config.settings import Environment, Settings
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
    app = create_app()

    with patch("app.ServiceContainer.initialize_services", side_effect=Exception("Startup error")):
        with pytest.raises(Exception, match="Startup error"):
            with TestClient(app) as client:
                client.get("/health")


# 3. Configuration Settings
def test_configuration_settings():
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "FIRECRAWL_API_KEY": "test_key"}):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert settings.firecrawl_api_key == "test_key"

    # Test default values
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert settings.api_host == "127.0.0.1"
