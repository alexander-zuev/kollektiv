import pytest

from src.infra.external.chroma_client import ChromaClient


@pytest.mark.integration
class TestChromaClientIntegration:
    """Integration tests for ChromaClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test that ChromaClient can initialize and connect to ChromaDB server."""
        # Create client
        chroma_client = await ChromaClient.create_client()

        # Verify client is initialized
        assert chroma_client is not None

        # Verify connection is alive
        await chroma_client.heartbeat()
