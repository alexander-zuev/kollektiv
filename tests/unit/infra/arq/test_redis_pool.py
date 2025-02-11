from unittest.mock import AsyncMock, Mock, patch

import pytest
from arq import ArqRedis

from src.infra.arq.arq_settings import ArqSettings
from src.infra.arq.redis_pool import RedisPool


@pytest.fixture
def mock_arq_settings():
    """Mock ARQ settings for testing."""
    settings = Mock(spec=ArqSettings)
    settings.redis_settings = Mock()
    settings.job_serializer = Mock()
    settings.job_deserializer = Mock()
    settings.connection_retries = 3
    return settings


@pytest.fixture
def redis_pool(mock_arq_settings):
    """Create RedisPool instance with mocked settings."""
    return RedisPool(arq_settings=mock_arq_settings)


def test_redis_pool_initialization(redis_pool, mock_arq_settings):
    """Test RedisPool initialization."""
    assert redis_pool.arq_settings == mock_arq_settings
    assert redis_pool._pool is None
    assert not redis_pool.is_connected


def test_is_connected_property(redis_pool):
    """Test is_connected property behavior."""
    assert not redis_pool.is_connected
    redis_pool._pool = Mock(spec=ArqRedis)
    assert redis_pool.is_connected


@pytest.mark.asyncio
async def test_initialize_pool_success(redis_pool):
    """Test successful pool initialization."""
    mock_pool = Mock(spec=ArqRedis)

    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(return_value=mock_pool)) as mock_create:
        await redis_pool.initialize_pool()

        # Verify pool was created with correct settings
        mock_create.assert_called_once_with(
            settings_=redis_pool.arq_settings.redis_settings,
            job_serializer=redis_pool.arq_settings.job_serializer,
            job_deserializer=redis_pool.arq_settings.job_deserializer,
            retry=redis_pool.arq_settings.connection_retries,
        )

        assert redis_pool._pool == mock_pool
        assert redis_pool.is_connected


@pytest.mark.asyncio
async def test_initialize_pool_already_connected(redis_pool):
    """Test initialize_pool when already connected."""
    redis_pool._pool = Mock(spec=ArqRedis)

    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock()) as mock_create:
        await redis_pool.initialize_pool()
        mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_initialize_pool_failure(redis_pool):
    """Test pool initialization failure."""
    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(side_effect=ConnectionError("Failed to connect"))):
        with pytest.raises(ConnectionError, match="Failed to connect"):
            await redis_pool.initialize_pool()

        assert redis_pool._pool is None
        assert not redis_pool.is_connected


@pytest.mark.asyncio
async def test_create_redis_pool_success():
    """Test create_redis_pool class method."""
    mock_pool = Mock(spec=ArqRedis)

    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(return_value=mock_pool)):
        pool = await RedisPool.create_redis_pool()
        assert isinstance(pool, ArqRedis)
        assert pool == mock_pool


@pytest.mark.asyncio
async def test_create_redis_pool_failure():
    """Test create_redis_pool failure."""
    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(side_effect=ConnectionError("Failed to connect"))):
        with pytest.raises(ConnectionError, match="Failed to connect"):
            await RedisPool.create_redis_pool()


@pytest.mark.asyncio
async def test_get_pool_success(redis_pool):
    """Test get_pool with successful connection."""
    mock_pool = Mock(spec=ArqRedis)

    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(return_value=mock_pool)):
        pool = await redis_pool.get_pool()
        assert pool == mock_pool
        assert redis_pool.is_connected


@pytest.mark.asyncio
async def test_get_pool_failure(redis_pool):
    """Test get_pool with connection failure."""
    with patch("src.infra.arq.redis_pool.create_pool", AsyncMock(side_effect=ConnectionError("Failed to connect"))):
        with pytest.raises(ConnectionError, match="Failed to connect"):
            await redis_pool.get_pool()

        assert not redis_pool.is_connected
