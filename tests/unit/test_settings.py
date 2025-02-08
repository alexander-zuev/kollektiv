import os
from unittest.mock import patch

import pytest

from src.api.routes import Routes
from src.infra.settings import Environment, Settings


def test_environment_independent_settings():
    """Test settings that should be the same regardless of environment."""
    settings = Settings()

    # These should be constant regardless of environment
    assert settings.firecrawl_api_url == "https://api.firecrawl.dev/v1"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8080
    assert settings.debug is True
    assert settings.max_retries == 3
    assert settings.backoff_factor == 2.0
    assert settings.default_page_limit == 25
    assert settings.default_max_depth == 5


def test_path_settings():
    """Test path configurations that are environment-independent."""
    settings = Settings()

    # Verify paths exist (not directories)
    assert settings.src_dir.exists()
    assert settings.eval_dir.parent.exists()  # Check parent since these are relative paths
    assert settings.prompt_dir.parent.exists()
    assert settings.tools_dir.parent.exists()
    assert isinstance(settings.prompts_file, str)  # These are now strings, not paths
    assert isinstance(settings.tools_file, str)


def test_environment_specific_settings():
    """Test environment-specific settings based on current environment."""
    current_env = os.getenv("ENVIRONMENT", "local")
    settings = Settings()

    if current_env == "staging":
        assert settings.environment == Environment.STAGING
        assert settings.public_url.startswith("https://")  # Using public_url instead of base_url
        assert settings.firecrawl_webhook_url == f"{settings.public_url}{Routes.System.Webhooks.FIRECRAWL}"
    else:
        assert settings.environment == Environment.LOCAL
        expected_url = f"http://{settings.api_host}:{settings.api_port}"
        assert settings.public_url == expected_url  # Using public_url instead of base_url
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
        assert settings.public_url == f"http://{settings.api_host}:{settings.api_port}"  # Using public_url

    # Test STAGING override
    with patch.dict(os.environ, {"ENVIRONMENT": "staging", "RAILWAY_PUBLIC_DOMAIN": "test.railway.app"}):
        settings = Settings()
        assert settings.environment == Environment.STAGING
        assert settings.public_url == "https://test.railway.app"  # Using public_url with railway domain


@pytest.mark.skipif("CI" in os.environ, reason="Local environment test only")
def test_production_environment_validation():
    """Test that production environment requires RAILWAY_PUBLIC_DOMAIN."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
        settings = Settings()
        with pytest.raises(ValueError, match="RAILWAY_PUBLIC_DOMAIN must be set in staging/production"):
            _ = settings.public_url  # Using public_url instead of base_url


@pytest.mark.skipif("CI" in os.environ, reason="Local environment test only")
def test_local_env_file_loading():
    """Test .env file loading in local environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        settings = Settings()
        assert settings.environment == Environment.LOCAL
        assert settings.public_url.startswith("http://127.0.0.1")  # Using public_url


@pytest.mark.skipif("CI" not in os.environ, reason="CI environment test only")
def test_ci_environment_settings():
    """Test settings specifically in CI environment."""
    settings = Settings()
    assert settings.environment == Environment.STAGING
    # In CI, we should have RAILWAY_PUBLIC_DOMAIN set
    assert settings.railway_public_domain is not None
    assert settings.public_url.startswith("https://")
    assert all(
        key is not None
        for key in [
            settings.firecrawl_api_key,
            settings.anthropic_api_key,
            settings.openai_api_key,
            settings.cohere_api_key,
        ]
    )
