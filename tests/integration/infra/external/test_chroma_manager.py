import pytest

from src.infra.external.chroma_manager import ChromaManager


@pytest.mark.integration
class TestChromaManagerIntegration:
    """Integration tests for ChromaManager with real ChromaDB."""

    @pytest.mark.asyncio
    async def test_connection_and_heartbeat(self):
        """Test that ChromaManager can connect and verify connection."""
        manager = await ChromaManager.create_async()
        client = await manager.get_async_client()

        # Verify connection is alive
        await client.heartbeat()

    @pytest.mark.asyncio
    async def test_client_reuse(self):
        """Test that manager properly reuses the client."""
        manager = ChromaManager()

        client1 = await manager.get_async_client()
        client2 = await manager.get_async_client()

        assert client1 is client2
        await client1.heartbeat()  # Verify the connection still works
