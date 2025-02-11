"""Integration tests for Redis pool."""

import pytest
from arq import ArqRedis

from src.infra.arq.arq_settings import get_arq_settings
from src.infra.arq.redis_pool import RedisPool
from src.infra.settings import get_settings

settings = get_settings()
arq_settings = get_arq_settings()


@pytest.fixture(scope="function")
async def redis_pool(redis_integration_manager):
    """Create a RedisPool instance for testing."""
    pool = RedisPool()
    yield pool
    # Cleanup
    if pool.is_connected and pool._pool:
        await pool._pool.close()


@pytest.mark.asyncio
async def test_redis_pool_settings_integration(redis_pool):
    """Test RedisPool integration with settings."""
    # Verify settings integration
    assert redis_pool.arq_settings.redis_host == settings.redis_host
    assert redis_pool.arq_settings.redis_port == settings.redis_port
    assert redis_pool.arq_settings.redis_user == settings.redis_user
    assert redis_pool.arq_settings.redis_password == settings.redis_password
    assert redis_pool.arq_settings.connection_retries == 5  # Default from arq_settings


@pytest.mark.asyncio
async def test_redis_pool_get_pool(redis_pool):
    """Test get_pool method - the main way other services get Redis access."""
    # Act
    redis = await redis_pool.get_pool()

    # Assert
    assert isinstance(redis, ArqRedis)
    assert redis_pool.is_connected
    assert await redis.ping() is True  # Verify actual Redis connection


@pytest.mark.asyncio
async def test_redis_pool_factory_method(redis_integration_manager):
    """Test the static factory method - used by worker services."""
    # Act
    redis = await RedisPool.create_redis_pool()

    try:
        # Assert
        assert isinstance(redis, ArqRedis)
        assert await redis.ping() is True  # Verify actual Redis connection
    finally:
        # Cleanup
        await redis.close()
