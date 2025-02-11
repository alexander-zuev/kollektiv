from arq.connections import RedisSettings

from src.infra.arq.arq_settings import ArqSettings, get_arq_settings
from src.infra.arq.serializer import deserialize, serialize
from src.infra.settings import get_settings

settings = get_settings()


def test_arq_settings_initialization():
    """Test basic initialization of ARQ settings."""
    arq_settings = ArqSettings()

    # Test default values
    assert arq_settings.job_retries == 3
    assert arq_settings.health_check_interval == 60
    assert arq_settings.max_jobs == 1000
    assert arq_settings.connection_retries == 5


def test_redis_settings_property():
    """Test Redis settings property creates correct RedisSettings instance."""
    arq_settings = ArqSettings()

    # First call - should create new settings
    redis_settings = arq_settings.redis_settings
    assert isinstance(redis_settings, RedisSettings)
    assert redis_settings.host == settings.redis_host
    assert redis_settings.port == settings.redis_port
    assert redis_settings.username == settings.redis_user
    assert redis_settings.password == settings.redis_password

    # Second call - should return cached settings
    cached_settings = arq_settings.redis_settings
    assert cached_settings is redis_settings  # Should be same instance


def test_job_serializer_property():
    """Test job serializer property returns correct serializer function."""
    arq_settings = ArqSettings()

    # First call - should set and return serializer
    serializer = arq_settings.job_serializer
    assert serializer == serialize
    assert callable(serializer)

    # Second call - should return cached serializer
    cached_serializer = arq_settings.job_serializer
    assert cached_serializer is serializer  # Should be same instance


def test_job_deserializer_property():
    """Test job deserializer property returns correct deserializer function."""
    arq_settings = ArqSettings()

    # First call - should set and return deserializer
    deserializer = arq_settings.job_deserializer
    assert deserializer == deserialize
    assert callable(deserializer)

    # Second call - should return cached deserializer
    cached_deserializer = arq_settings.job_deserializer
    assert cached_deserializer is deserializer  # Should be same instance


def test_get_arq_settings_caching():
    """Test that get_arq_settings caches and returns the same instance."""
    # First call
    settings1 = get_arq_settings()
    assert isinstance(settings1, ArqSettings)

    # Second call - should return same instance
    settings2 = get_arq_settings()
    assert settings2 is settings1  # Should be same instance


def test_arq_settings_with_custom_values():
    """Test ArqSettings respects custom values from environment."""
    custom_settings = ArqSettings(job_retries=5, health_check_interval=120, max_jobs=2000, connection_retries=10)

    # Test the actual configurable values
    assert custom_settings.job_retries == 5
    assert custom_settings.health_check_interval == 120
    assert custom_settings.max_jobs == 2000
    assert custom_settings.connection_retries == 10

    # Redis settings should come from settings.redis_url, not direct host/port
    redis_settings = custom_settings.redis_settings
    assert isinstance(redis_settings, RedisSettings)
    # We should test that it uses the URL from settings
    assert redis_settings == RedisSettings.from_dsn(settings.redis_url)
