from unittest.mock import Mock, patch

import pytest

from src.infrastructure.config.settings import settings
from src.infrastructure.external.supabase_client import SupabaseClient


@pytest.fixture
def mock_create_client():
    """Mock the Supabase create_client function."""
    with patch("src.infrastructure.external.supabase_client.create_client") as mock:
        mock.return_value = Mock()  # Return a mock client
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

    def test_initialization_failure(self, mock_create_client):
        """Test that initialization failure is handled properly."""
        # Arrange
        mock_create_client.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            SupabaseClient()
        assert str(exc_info.value) == "Connection failed"
