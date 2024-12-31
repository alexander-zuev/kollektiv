from unittest.mock import patch

import pytest

from src.infra.external.chroma_manager import ChromaManager


@pytest.mark.unit
class TestChromaManager:
    """Unit tests for ChromaManager."""

    def test_initialization(self):
        """Test that ChromaManager initializes with None client."""
        manager = ChromaManager()
        assert manager._client is None

    def test_parse_url(self):
        """Test URL parsing."""
        test_url = "http://localhost:8000"
        host, port = ChromaManager._parse_url(test_url)
        assert host == "localhost"
        assert port == 8000

    @pytest.mark.asyncio
    async def test_connect_async(self, mock_chroma_client):
        """Test async connection."""
        manager = ChromaManager()

        with patch("chromadb.AsyncHttpClient", return_value=mock_chroma_client):
            await manager._connect_async()

            assert manager._client is mock_chroma_client
            mock_chroma_client.heartbeat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_async(self, mock_chroma_client):
        """Test create_async class method."""
        with patch("chromadb.AsyncHttpClient", return_value=mock_chroma_client):
            manager = await ChromaManager.create_async()

            assert isinstance(manager, ChromaManager)
            assert manager._client is mock_chroma_client
            mock_chroma_client.heartbeat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_async_client(self, mock_chroma_client):
        """Test get_async_client method."""
        with patch("chromadb.AsyncHttpClient", return_value=mock_chroma_client):
            manager = ChromaManager()
            client = await manager.get_async_client()

            assert client is mock_chroma_client
            mock_chroma_client.heartbeat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_async_client_reuse(self, mock_chroma_client):
        """Test that get_async_client reuses existing client."""
        with patch("chromadb.AsyncHttpClient", return_value=mock_chroma_client):
            manager = ChromaManager()

            client1 = await manager.get_async_client()
            client2 = await manager.get_async_client()

            assert client1 is client2
            assert mock_chroma_client.heartbeat.await_count == 1  # Only called once
