from unittest.mock import AsyncMock, patch

import pytest

from src.infra.external.chroma_client import ChromaClient
from src.infra.settings import settings


@pytest.mark.unit
class TestChromaClient:
    """Unit tests for ChromaClient."""

    def test_initialization(self):
        """Test that ChromaClient initializes with None client."""
        client = ChromaClient()
        assert client.client is None

    @pytest.mark.asyncio
    async def test_create_client(self):
        """Test create_client class method."""
        # Mock the AsyncHttpClient and heartbeat
        mock_client = AsyncMock()
        mock_client.heartbeat = AsyncMock()

        with patch("chromadb.AsyncHttpClient", return_value=mock_client) as mock_http_client:
            chroma_client = await ChromaClient.create_client()

            # Verify ChromaClient was created with correct configuration
            mock_http_client.assert_called_once_with(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )

            # Verify heartbeat was called
            mock_client.heartbeat.assert_called_once()

            # Verify client is properly set
            assert chroma_client.client == mock_client

    @pytest.mark.asyncio
    async def test_create_client_custom_host_port(self):
        """Test create_client with custom host and port."""
        custom_host = "custom_host"
        custom_port = 9000

        # Mock the AsyncHttpClient and heartbeat
        mock_client = AsyncMock()
        mock_client.heartbeat = AsyncMock()

        with patch("chromadb.AsyncHttpClient", return_value=mock_client) as mock_http_client:
            chroma_client = await ChromaClient.create_client(host=custom_host, port=custom_port)

            # Verify ChromaClient was created with custom configuration
            mock_http_client.assert_called_once_with(
                host=custom_host,
                port=custom_port,
            )

            # Verify client is properly set
            assert chroma_client.client == mock_client
