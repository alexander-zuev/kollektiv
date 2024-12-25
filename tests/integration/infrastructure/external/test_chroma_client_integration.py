import pytest

from src.infrastructure.external.chroma_client import ChromaClient


@pytest.mark.integration
class TestChromaClientIntegration:
    """Integration tests for ChromaClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test that ChromaClient can initialize and connect to ChromaDB server."""
        # Create client
        chroma_client = await ChromaClient.create_client()

        # Verify client is initialized
        assert chroma_client.client is not None

        # Verify connection is alive
        await chroma_client.client.heartbeat()

    @pytest.mark.asyncio
    async def test_client_custom_connection(self):
        """Test that ChromaClient can connect with custom host/port."""
        # Create client with custom connection (using default values to ensure it works)
        chroma_client = await ChromaClient.create_client(host="localhost", port=8000)

        # Verify client is initialized and connected
        assert chroma_client.client is not None
        await chroma_client.client.heartbeat()
