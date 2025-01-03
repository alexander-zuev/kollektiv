from unittest.mock import AsyncMock, patch

import pytest

from src.infra.external.redis_manager import RedisManager


class TestRedisManager:
    """Unit tests for RedisManager."""

    def test_init_default(self):
        """Test default initialization."""
        manager = RedisManager()
        assert manager._decode_responses is True
        assert manager._sync_client is None
        assert manager._async_client is None

    def test_init_custom(self):
        """Test initialization with custom decode_responses."""
        manager = RedisManager(decode_responses=False)
        assert manager._decode_responses is False
        assert manager._sync_client is None
        assert manager._async_client is None

    def test_create_sync_client(self, mock_sync_redis):
        """Test sync client creation."""
        with patch("redis.Redis.from_url", return_value=mock_sync_redis):
            manager = RedisManager()
            client = manager._create_sync_client(decode_responses=True)
            assert client is mock_sync_redis

    @pytest.mark.asyncio
    async def test_create_async_client(self, mock_async_redis):
        """Test async client creation."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = RedisManager()
            client = manager._create_async_client(decode_responses=True)
            assert client is mock_async_redis

    def test_connect_sync_success(self, mock_sync_redis):
        """Test successful sync connection."""
        with patch("redis.Redis.from_url", return_value=mock_sync_redis):
            manager = RedisManager()
            manager._connect_sync()
            assert manager._sync_client is mock_sync_redis
            mock_sync_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_async_success(self, mock_async_redis):
        """Test successful async connection."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = RedisManager()
            await manager._connect_async()
            assert manager._async_client is mock_async_redis
            mock_async_redis.ping.assert_awaited_once()

    def test_create_classmethod(self, mock_sync_redis):
        """Test create classmethod."""
        with patch("redis.Redis.from_url", return_value=mock_sync_redis):
            manager = RedisManager.create()
            assert isinstance(manager, RedisManager)
            assert manager._sync_client is mock_sync_redis
            mock_sync_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_async_classmethod(self, mock_async_redis):
        """Test create_async classmethod."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = await RedisManager.create_async()
            assert isinstance(manager, RedisManager)
            assert manager._async_client is mock_async_redis
            mock_async_redis.ping.assert_called_once()

    def test_get_sync_client(self, mock_sync_redis):
        """Test get_sync_client method."""
        with patch("redis.Redis.from_url", return_value=mock_sync_redis):
            manager = RedisManager()
            client = manager.get_sync_client()
            assert client is mock_sync_redis
            mock_sync_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_client(self, mock_async_redis):
        """Test get_async_client method."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = RedisManager()
            client = await manager.get_async_client()
            assert client is mock_async_redis
            mock_async_redis.ping.assert_called_once()

    def test_get_sync_client_reuses_existing(self, mock_sync_redis):
        """Test get_sync_client reuses existing client."""
        with patch("redis.Redis.from_url", return_value=mock_sync_redis):
            manager = RedisManager()
            client1 = manager.get_sync_client()
            client2 = manager.get_sync_client()
            assert client1 is client2
            mock_sync_redis.ping.assert_called_once()  # Only called once for first connection

    @pytest.mark.asyncio
    async def test_get_async_client_reuses_existing(self, mock_async_redis):
        """Test get_async_client reuses existing client."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = RedisManager()
            client1 = await manager.get_async_client()
            client2 = await manager.get_async_client()
            assert client1 is client2
            assert mock_async_redis.ping.call_count == 1  # Only called once for first connection

    @pytest.mark.asyncio
    async def test_connect_async_error(self, mock_async_redis):
        """Test async connection error handling."""
        mock_async_redis.ping = AsyncMock(side_effect=ConnectionError("Test error"))
        with patch("redis.asyncio.Redis.from_url", return_value=mock_async_redis):
            manager = RedisManager()
            with pytest.raises(ConnectionError):
                await manager._connect_async()
