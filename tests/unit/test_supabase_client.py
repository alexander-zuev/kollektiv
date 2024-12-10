from unittest.mock import Mock, AsyncMock, patch

import pytest

from src.infrastructure.config.settings import settings
from src.infrastructure.external.supabase_client import SupabaseClient


@pytest.fixture
def mock_create_client():
    """Mock the Supabase create_client function."""
    with patch("src.infrastructure.external.supabase_client.get_client") as mock:
        mock.return_value = Mock()  # Return a mock client
        yield mock


@pytest.fixture
def mock_create_async_client():
    """Mock the Supabase async client creation."""
    with patch("src.infrastructure.external.supabase_client.get_client") as mock:
        mock.return_value = AsyncMock()  # Return an async mock client
        yield mock


class TestSupabaseClient:
    """Test suite for SupabaseClient."""

    def test_successful_initialization(self, mock_create_client):
        """Test that client initializes successfully with default settings."""
        # Act
        client = SupabaseClient()

        # Assert
        mock_create_client.assert_called_once_with(
            supabase_url=settings.supabase_url, supabase_key=settings.supabase_key
        )
        assert client._client is not None

    async def test_connection_failure(self, mock_create_async_client):
        """Test that connection failure is handled properly."""
        # Arrange
        mock_create_async_client.side_effect = Exception("Connection failed")
        client = SupabaseClient()

        # Act & Assert
        with pytest.raises(Exception):
            await client.connect()

    def test_initialization_failure(self, mock_create_client):
        """Test that initialization failure is handled properly."""
        # Arrange
        mock_create_client.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception):
            SupabaseClient()

    async def test_get_client(self, mock_create_async_client):
        """Test that get_client connects if not already connected."""
        # Arrange
        client = SupabaseClient()

        # Act
        result = await client.get_client()

        # Assert
        mock_create_async_client.assert_called_once()
        assert result == client._client
