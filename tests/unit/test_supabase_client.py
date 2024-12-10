from unittest.mock import AsyncMock, Mock, patch

import pytest
from supabase import AsyncClient

from src.infrastructure.config.settings import settings
from src.infrastructure.external.supabase_client import SupabaseClient


@pytest.fixture
def mock_create_client():
    """Mock the Supabase create_async_client function."""
    with patch("src.infrastructure.external.supabase_client.create_async_client") as mock:
        mock_client = AsyncMock(spec=AsyncClient)
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def mock_supabase_client(mock_create_client):
    """Create a SupabaseClient instance with mocked async client."""
    return SupabaseClient()


class TestSupabaseClient:
    """Test suite for SupabaseClient."""

    @pytest.mark.asyncio
    async def test_successful_initialization(self, mock_supabase_client, mock_create_client):
        """Test that client initializes successfully with default settings."""
        # Assert initialization
        assert mock_supabase_client._client is None

        # Test connection
        await mock_supabase_client.connect()

        # Verify client creation
        mock_create_client.assert_called_once_with(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key,
        )
        assert mock_supabase_client._client is not None

    @pytest.mark.asyncio
    async def test_connection_failure(self, mock_create_client):
        """Test that connection failure is handled properly."""
        # Arrange
        mock_create_client.side_effect = Exception("Connection failed")
        client = SupabaseClient()

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            await client.connect()

    @pytest.mark.asyncio
    async def test_get_client_connects_if_needed(self, mock_supabase_client):
        """Test that get_client connects if not already connected."""
        # Initial state
        assert mock_supabase_client._client is None

        # Get client should trigger connection
        client = await mock_supabase_client.get_client()
        assert client is not None
        assert mock_supabase_client._client is client

        # Second call should return existing client
        second_client = await mock_supabase_client.get_client()
        assert second_client is client
