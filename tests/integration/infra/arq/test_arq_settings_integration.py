import pytest
from arq.connections import RedisSettings

from src.infra.arq.arq_settings import ArqSettings, get_arq_settings
from src.infra.arq.serializer import deserialize, serialize
from src.infra.settings import get_settings

settings = get_settings()


@pytest.fixture
def arq_settings():
    """Get a fresh instance of ARQ settings."""
    return ArqSettings()


def test_redis_settings_integration(arq_settings):
    """Test Redis settings integration with actual configuration."""
    redis_settings = arq_settings.redis_settings

    # Test that we get a proper RedisSettings instance
    assert isinstance(redis_settings, RedisSettings)

    # Test that settings are created from DSN
    expected_settings = RedisSettings.from_dsn(settings.redis_url)
    assert redis_settings.host == expected_settings.host
    assert redis_settings.port == expected_settings.port
    assert redis_settings.username == expected_settings.username
    assert redis_settings.password == expected_settings.password

    # Test caching behavior
    cached_settings = arq_settings.redis_settings
    assert cached_settings is redis_settings  # Should return the same instance


def test_redis_settings_from_env(arq_settings):
    """Test that Redis settings match environment configuration."""
    redis_settings = arq_settings.redis_settings

    # Should match our environment settings
    assert redis_settings.host == settings.redis_host
    assert redis_settings.port == settings.redis_port
    assert redis_settings.username == settings.redis_user
    assert redis_settings.password == settings.redis_password


def test_serializer_integration(arq_settings):
    """Test serializer/deserializer integration with actual implementation."""
    assert arq_settings.job_serializer == serialize
    assert arq_settings.job_deserializer == deserialize

    # Test that they're actually callable
    assert callable(arq_settings.job_serializer)
    assert callable(arq_settings.job_deserializer)


def test_settings_singleton():
    """Test that get_arq_settings returns the same instance."""
    settings1 = get_arq_settings()
    settings2 = get_arq_settings()

    assert settings1 is settings2
    assert isinstance(settings1, ArqSettings)

    # Test that the settings are properly configured
    assert settings1.job_retries == 3
    assert settings1.health_check_interval == 60
    assert settings1.max_jobs == 1000
    assert settings1.connection_retries == 5
