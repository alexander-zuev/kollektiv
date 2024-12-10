"""Test settings configuration."""
from pathlib import Path
from typing import Any

from src.infrastructure.config.settings import Settings, Environment


class TestSettings(Settings):
    """Test settings with default values for testing."""

    def __init__(self, **values: Any):
        """Initialize test settings with default values."""
        test_values = {
            "ENVIRONMENT": Environment.LOCAL.value,  # Use environment variable name with enum value
            "FIRECRAWL_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key",
            "OPENAI_API_KEY": "test-key",
            "COHERE_API_KEY": "test-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key",
            "LOGFIRE_TOKEN": "test-key",
            "REDIS_URL": "redis://localhost:6379",
            "log_level": "DEBUG",
            "src_dir": Path(__file__).parent,
            "use_ngrok": False,
        }
        test_values.update(values)
        super().__init__(**test_values)
