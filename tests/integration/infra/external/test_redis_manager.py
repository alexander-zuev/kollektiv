import pytest

from src.infra.external.redis_manager import RedisManager


@pytest.mark.integration
class TestRedisManagerIntegration:
    """Integration tests for RedisManager with real Redis."""

    @pytest.mark.asyncio
    async def test_async_client_initialization(self, redis_test_client):
        """Test async client creation and connection with real Redis."""
        manager = RedisManager()
        client = await manager.get_async_client()

        # Verify client works
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
    async def test_decode_responses_setting(self):
        """Test decode_responses setting is respected."""
        # Test with decode_responses=False
        binary_manager = RedisManager(decode_responses=False)
        binary_client = await binary_manager.get_async_client()
        await binary_client.set("binary_test", "value")
        result = await binary_client.get("binary_test")
        assert isinstance(result, bytes)

        # Test with decode_responses=True (default)
        text_manager = RedisManager()
        text_client = await text_manager.get_async_client()
        await text_client.set("text_test", "value")
        result = await text_client.get("text_test")
        assert isinstance(result, str)
