from unittest.mock import AsyncMock, patch

import pytest
from chromadb.api.async_api import AsyncClientAPI

from src.infrastructure.external.chroma_client import ChromaClient


@pytest.mark.asyncio
async def test_create_client_success():
    """Test successful creation of Chroma client."""
    mock_client = AsyncMock(spec=AsyncClientAPI)
    with patch("chromadb.AsyncHttpClient", return_value=mock_client) as mock_http_client:
        client = await ChromaClient.create_client(host="test_host", port=1234)
        mock_http_client.assert_called_once_with(host="test_host", port=1234)
        assert isinstance(client, ChromaClient)
        assert client.client == mock_client


@pytest.mark.asyncio
async def test_create_client_default_values():
    """Test successful creation of Chroma client with default host and port."""
    mock_client = AsyncMock(spec=AsyncClientAPI)
    with patch("chromadb.AsyncHttpClient", return_value=mock_client) as mock_http_client:
        client = await ChromaClient.create_client()
        mock_http_client.assert_called_once_with(host="localhost", port=8000)
        assert isinstance(client, ChromaClient)
        assert client.client == mock_client


# Integration test - requires a ChromaDB instance running
@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_client_integration():
    """Integration test to check if client can connect to ChromaDB."""
    try:
        client = await ChromaClient.create_client()
        assert isinstance(client, ChromaClient)
        # Attempt a simple operation to check connection
        await client.client.heartbeat()
    except Exception as e:
        pytest.fail(f"Failed to connect to ChromaDB: {e}")
