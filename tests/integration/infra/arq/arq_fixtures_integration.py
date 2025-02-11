"""Common fixtures for ARQ integration tests."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.infra.arq.worker import WorkerSettings
from src.infra.arq.worker_services import WorkerServices


@pytest.fixture
async def mock_worker_services():
    """Create a mock worker services instance."""
    mock_services = AsyncMock(spec=WorkerServices)
    mock_services.arq_redis_pool = Mock()
    mock_services.shutdown_services = AsyncMock()
    return mock_services


@pytest.fixture
def worker_settings():
    """Create a worker settings instance."""
    return WorkerSettings()


@pytest.fixture
async def mock_worker_context(mock_worker_services):
    """Create a mock worker context."""
    ctx = {
        "worker_services": mock_worker_services,
        "arq_redis": mock_worker_services.arq_redis_pool,
    }
    return ctx
