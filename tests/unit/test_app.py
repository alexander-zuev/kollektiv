from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from src.app import lifespan
from src.infra.service_container import ServiceContainer


@pytest.mark.unit
def test_app_basic_configuration(mock_app):
    """Test basic FastAPI app configuration."""
    assert mock_app.title == "Kollektiv API"
    assert mock_app.description == "RAG-powered LLM chat application"
    # Test error handlers are registered
    assert mock_app.exception_handlers is not None
    assert Exception in mock_app.exception_handlers


@pytest.mark.unit
async def test_startup_error_handling():
    """Test error handling during startup."""
    app = FastAPI()
    with patch("src.infra.settings.settings.environment", "staging"):
        with patch("src.app.ServiceContainer.create", side_effect=Exception("Startup failed")):
            with pytest.raises(Exception, match="Startup failed"):
                async with lifespan(app):
                    pass


@pytest.mark.unit
async def test_shutdown_services():
    """Test services are properly shutdown."""
    app = FastAPI()
    mock_container = AsyncMock(spec=ServiceContainer)

    with patch("src.app.ServiceContainer.create", return_value=mock_container):
        async with lifespan(app):
            pass

    mock_container.shutdown_services.assert_awaited_once()
