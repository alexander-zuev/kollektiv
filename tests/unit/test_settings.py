import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.api.routes import Routes
from src.infrastructure.config.settings import Environment, Settings


def test_environment_independent_settings():
    """Test settings that should be the same regardless of environment."""
    settings = Settings()

    # These should be constant regardless of environment
    assert settings.firecrawl_api_url == "https://api.firecrawl.dev/v1"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.chainlit_host == "127.0.0.1"
    assert settings.chainlit_port == 8001
    assert settings.log_level == "debug"
    assert settings.max_retries == 3
    assert settings.backoff_factor == 2.0
    assert settings.default_page_limit == 25
    assert settings.default_max_depth == 5


def test_path_settings():
    """Test path configurations that are environment-independent."""
    settings = Settings()

    # Path structure should be consistent
    assert settings.log_dir == Path("src/logs")
    assert settings.raw_data_dir == Path("src/data/raw")
    assert settings.processed_data_dir == Path("src/data/processed")
    assert settings.chroma_db_dir == Path("src/infrastructure/storage/vector/chroma")

    # Verify directories exist
    for dir_path in [settings.log_dir, settings.raw_data_dir, settings.processed_data_dir, settings.chroma_db_dir]:
        assert dir_path.exists()
        assert dir_path.is_dir()


def test_environment_specific_settings():
    """Test environment-specific settings based on current environment."""
    current_env = os.getenv("ENVIRONMENT", "local")
    settings = Settings()

    if current_env == "staging":
        assert settings.environment == Environment.STAGING
        assert settings.base_url == "http://mock-api:8000"
        assert settings.firecrawl_webhook_url == f"http://mock-api:8000{Routes.System.Webhooks.FIRECRAWL}"
    else:
        assert settings.environment == Environment.LOCAL
        expected_url = f"http://{settings.api_host}:{settings.api_port}"
        assert settings.base_url == expected_url
        assert settings.firecrawl_webhook_url == f"{expected_url}{Routes.System.Webhooks.FIRECRAWL}"


def test_required_api_keys():
    """Test that required API keys are present."""
    settings = Settings()

    # These should be set in both environments
    assert settings.firecrawl_api_key is not None
    assert settings.anthropic_api_key is not None
    assert settings.openai_api_key is not None
    assert settings.cohere_api_key is not None


def test_environment_override():
    """Test that environment settings can be explicitly overridden."""
    # Test LOCAL override
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert settings.base_url == f"http://{settings.api_host}:{settings.api_port}"

    # Test STAGING override
    with patch.dict(os.environ, {"ENVIRONMENT": "staging", "BASE_URL": "http://mock-api:8000"}):
        settings = Settings()
        assert settings.environment == Environment.STAGING
        assert settings.base_url == "http://mock-api:8000"


@pytest.mark.skipif("CI" in os.environ, reason="Local environment test only")
def test_production_environment_validation():
    """Test that production environment requires BASE_URL."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):  # Add clear=True
        settings = Settings()
        with pytest.raises(ValueError, match="BASE_URL environment variable is required"):
            _ = settings.base_url


@pytest.mark.skipif("CI" in os.environ, reason="Local environment test only")
def test_local_env_file_loading():
    """Test .env file loading in local environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert "http://127.0.0.1" in settings.base_url


@pytest.mark.skipif("CI" not in os.environ, reason="CI environment test only")
def test_ci_environment_settings():
    """Test settings specifically in CI environment."""
    settings = Settings()
    assert settings.environment == Environment.STAGING
    assert settings.base_url == "http://mock-api:8000"
    assert all(
        key is not None
        for key in [
            settings.firecrawl_api_key,
            settings.anthropic_api_key,
            settings.openai_api_key,
            settings.cohere_api_key,
        ]
    )
