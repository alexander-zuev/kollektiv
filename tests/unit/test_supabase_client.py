from unittest.mock import AsyncMock, patch

import pytest

from src.infra.external.supabase_manager import SupabaseManager
from src.infra.settings import settings


@pytest.fixture
def mock_create_async_client():
    """Mock the Supabase create_async_client function."""
    with patch("src.infra.external.supabase_manager.create_async_client") as mock:
        mock.return_value = AsyncMock()  # Return an async mock client
        yield mock


class TestSupabaseClient:
    """Test suite for SupabaseClient."""

    async def test_successful_initialization(self, mock_create_async_client):
        """Test that initialization works properly."""
        # Arrange & Act
        manager = await SupabaseManager.create_async()

        # Assert
        mock_create_async_client.assert_called_once_with(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_role_key,
        )
        assert manager._client is mock_create_async_client.return_value

    async def test_connection_failure(self, mock_create_async_client):
        """Test that initialization failure is handled properly."""
        # Arrange
        mock_create_async_client.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await SupabaseManager.create_async()
        assert str(exc_info.value) == "Connection failed"

    async def test_get_client(self, mock_create_async_client):
        """Test that get_client connects if not already connected."""
        # Arrange
        manager = await SupabaseManager.create_async()

        # Act
        client = await manager.get_async_client()

        # Assert
        mock_create_async_client.assert_called_once()
        assert client is mock_create_async_client.return_value
