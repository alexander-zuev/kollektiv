import os
from pathlib import Path

import pytest

from src.api.routes import Routes
from src.infrastructure.config.settings import Environment, Settings


@pytest.fixture
def set_env_vars():
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["FIRECRAWL_API_KEY"] = "test_firecrawl_key"
    os.environ["ANTHROPIC_API_KEY"] = "test_anthropic_key"
    os.environ["OPENAI_API_KEY"] = "test_openai_key"
    os.environ["COHERE_API_KEY"] = "test_cohere_key"
    os.environ["WEAVE_PROJECT_NAME"] = "test_project"
    os.environ["BASE_URL"] = "https://staging.example.com"
    yield
    # Cleanup
    for var in [
        "ENVIRONMENT",
        "FIRECRAWL_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "COHERE_API_KEY",
        "WEAVE_PROJECT_NAME",
        "BASE_URL",
    ]:
        os.environ.pop(var, None)


def test_environment_loading(set_env_vars):
    settings = Settings()
    assert settings.environment == Environment.STAGING
    assert settings.firecrawl_api_key == "test_firecrawl_key"
    assert settings.anthropic_api_key == "test_anthropic_key"
    assert settings.openai_api_key == "test_openai_key"
    assert settings.cohere_api_key == "test_cohere_key"
    assert settings.weave_project_name == "test_project"


def test_default_values():
    settings = Settings()
    assert settings.environment == Environment.LOCAL
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


def test_path_construction():
    settings = Settings()
    assert settings.log_dir == Path("src/logs")
    assert settings.raw_data_dir == Path("src/data/raw")
    assert settings.processed_data_dir == Path("src/data/processed")
    assert settings.chroma_db_dir == Path("src/infrastructure/storage/vector/chroma")


def test_directory_creation():
    settings = Settings()
    for dir_path in [
        settings.log_dir,
        settings.raw_data_dir,
        settings.processed_data_dir,
        settings.chroma_db_dir,
    ]:
        assert dir_path.exists()
        assert dir_path.is_dir()


def test_base_url_local():
    settings = Settings(environment=Environment.LOCAL)
    expected_url = f"http://{settings.api_host}:{settings.api_port}"
    assert settings.base_url == expected_url


def test_base_url_staging(set_env_vars):
    settings = Settings(environment=Environment.STAGING)
    assert settings.base_url == "https://staging.example.com"


def test_firecrawl_webhook_url(set_env_vars):
    settings = Settings()
    expected_url = f"https://staging.example.com{Routes.System.Webhooks.FIRECRAWL}"

    assert settings.firecrawl_webhook_url == expected_url


def test_missing_base_url_in_production():
    os.environ["ENVIRONMENT"] = "production"
    os.environ.pop("BASE_URL", None)
    settings = Settings()

    with pytest.raises(ValueError, match="BASE_URL environment variable is required"):
        _ = settings.base_url

    os.environ.pop("ENVIRONMENT", None)


@pytest.mark.skipif("CI" in os.environ, reason="Skipping .env file test in CI environment")
def test_env_file_loading(monkeypatch):
    monkeypatch.setenv("ENV_FILE", "config/environments/.env")
    settings = Settings()
    # Assuming .env contains `ENVIRONMENT=local`
    assert settings.environment == Environment.LOCAL


@pytest.mark.skipif("CI" not in os.environ, reason="Only runs in CI environment")
def test_settings_initialization_in_ci():
    if "CI" in os.environ:
        settings = Settings()
        assert settings.environment == Environment.STAGING
        assert settings.firecrawl_api_key is not None
        assert settings.openai_api_key is not None
        assert settings.anthropic_api_key is not None
        assert settings.cohere_api_key is not None
