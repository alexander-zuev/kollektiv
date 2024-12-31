import pytest

from src.infra.external.redis_manager import RedisManager


@pytest.mark.integration
class TestRedisManagerIntegration:
    """Integration tests for RedisManager with real Redis."""

    @pytest.mark.asyncio
    async def test_connection_and_operations(self, redis_integration_manager):
        """Test that RedisManager can connect and perform operations."""
        client = await redis_integration_manager.get_async_client()

        # Verify basic operations work
        await client.set("test_key", "test_value")
        result = await client.get("test_key")
        assert result == "test_value"

    def test_sync_client_initialization(self):
        """Test sync client creation and connection with real Redis."""
        manager = RedisManager()
        client = manager.get_sync_client()

        # Verify client works
        client.set("test_key", "test_value")
        result = client.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_client_reuse(self):
        """Test that both sync and async clients are reused."""
        manager = RedisManager()

        # Test sync client reuse
        sync1 = manager.get_sync_client()
        sync2 = manager.get_sync_client()
        assert sync1 is sync2

        # Test async client reuse
        async1 = await manager.get_async_client()
        async2 = await manager.get_async_client()
        assert async1 is async2

    @pytest.mark.asyncio
    async def test_decode_responses_setting(self, redis_integration_manager):
        """Test decode_responses setting is respected."""
        # First clean up any existing data
        client = await redis_integration_manager.get_async_client()
        await client.flushall()

        # Test with decode_responses=True (default)
        await client.set("text_test", "value")
        result = await client.get("text_test")
        assert isinstance(result, str)
        assert result == "value"

        # Create a new manager with decode_responses=False
        binary_manager = RedisManager(decode_responses=False)
        try:
            binary_client = await binary_manager.get_async_client()
            await binary_client.set("binary_test", "value")
            result = await binary_client.get("binary_test")
            assert isinstance(result, bytes)
            assert result.decode() == "value"
        finally:
            if binary_manager._async_client:
                await binary_manager._async_client.close()
                binary_manager._async_client = None
