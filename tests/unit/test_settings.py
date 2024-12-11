import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.api.routes import Routes
from src.infrastructure.config.settings import Environment, Settings


@pytest.fixture
def mock_settings():
    """Create a Settings instance with mocked environment variables."""
    env_vars = {
        "ENVIRONMENT": "local",
        "FIRECRAWL_API_KEY": "test_key",
        "ANTHROPIC_API_KEY": "test_key",
        "OPENAI_API_KEY": "test_key",
        "COHERE_API_KEY": "test_key",
        "SUPABASE_URL": "test_url",
        "SUPABASE_SERVICE_KEY": "test_key",
        "LOGFIRE_TOKEN": "test_token",
        "REDIS_URL": "redis://localhost:6379",
        "BASE_URL": "http://127.0.0.1:8000",
        "API_HOST": "127.0.0.1",
        "API_PORT": "8000",
        "CHAINLIT_HOST": "127.0.0.1",
        "CHAINLIT_PORT": "8001",
        "LOG_LEVEL": "debug",
        "MAX_RETRIES": "3",
        "BACKOFF_FACTOR": "2.0",
        "DEFAULT_PAGE_LIMIT": "25",
        "DEFAULT_MAX_DEPTH": "5"
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()
        # Ensure directories exist
        for dir_path in [settings.log_dir, settings.raw_data_dir,
                        settings.processed_data_dir, settings.chroma_db_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        return settings


def test_environment_independent_settings(mock_settings):
    """Test settings that should be the same regardless of environment."""
    # These should be constant regardless of environment
    assert mock_settings.firecrawl_api_url == "https://api.firecrawl.dev/v1"
    assert mock_settings.api_host == "127.0.0.1"
    assert mock_settings.api_port == 8000
    assert mock_settings.chainlit_host == "127.0.0.1"
    assert mock_settings.chainlit_port == 8001
    assert mock_settings.log_level == "debug"
    assert mock_settings.max_retries == 3
    assert mock_settings.backoff_factor == 2.0
    assert mock_settings.default_page_limit == 25
    assert mock_settings.default_max_depth == 5


def test_path_settings(mock_settings):
    """Test path configurations that are environment-independent."""
    # Path structure should be consistent
    assert mock_settings.log_dir == Path("src/logs")
    assert mock_settings.raw_data_dir == Path("src/data/raw")
    assert mock_settings.processed_data_dir == Path("src/data/processed")
    assert mock_settings.chroma_db_dir == Path("src/infrastructure/storage/vector/chroma")

    # Verify directories exist
    for dir_path in [mock_settings.log_dir, mock_settings.raw_data_dir, mock_settings.processed_data_dir, mock_settings.chroma_db_dir]:
        assert dir_path.exists()
        assert dir_path.is_dir()


def test_environment_specific_settings(mock_settings):
    """Test environment-specific settings based on current environment."""
    current_env = os.getenv("ENVIRONMENT", "local")

    if current_env == "staging":
        assert mock_settings.environment == Environment.STAGING
        assert mock_settings.base_url == "http://mock-api:8000"
        assert mock_settings.firecrawl_webhook_url == f"http://mock-api:8000{Routes.System.Webhooks.FIRECRAWL}"
    else:
        assert mock_settings.environment == Environment.LOCAL
        expected_url = f"http://{mock_settings.api_host}:{mock_settings.api_port}"
        assert mock_settings.base_url == expected_url
        assert mock_settings.firecrawl_webhook_url == f"{expected_url}{Routes.System.Webhooks.FIRECRAWL}"


def test_required_api_keys(mock_settings):
    """Test that required API keys are present."""
    # These should be set in both environments
    assert mock_settings.firecrawl_api_key is not None
    assert mock_settings.anthropic_api_key is not None
    assert mock_settings.openai_api_key is not None
    assert mock_settings.cohere_api_key is not None


def test_environment_override(mock_settings):
    """Test that environment settings can be explicitly overridden."""
    # Test LOCAL override
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert settings.base_url == f"http://{settings.api_host}:{settings.api_port}"

    # Test STAGING override
    staging_env = {
        "ENVIRONMENT": "staging",
        "BASE_URL": "http://mock-api:8000",
        "FIRECRAWL_API_KEY": "test_key",
        "ANTHROPIC_API_KEY": "test_key",
        "OPENAI_API_KEY": "test_key",
        "COHERE_API_KEY": "test_key",
        "SUPABASE_URL": "test_url",
        "SUPABASE_SERVICE_KEY": "test_key",
        "LOGFIRE_TOKEN": "test_token",
        "REDIS_URL": "redis://localhost:6379"
    }
    with patch.dict(os.environ, staging_env):
        settings = Settings()
        assert settings.environment == Environment.STAGING
        assert settings.base_url == "http://mock-api:8000"


@pytest.mark.skipif("CI" in os.environ, reason="Local environment test only")
def test_production_environment_validation():
    """Test that production environment requires BASE_URL."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
        settings = Settings()
        settings.environment = Environment.PRODUCTION  # Force production environment
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
