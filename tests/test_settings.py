"""Test settings configuration."""
from pathlib import Path
from typing import Any

from src.infrastructure.config.settings import Settings, Environment


class TestSettings(Settings):
    """Test settings with default values for testing."""

    def __init__(self, **values: Any):
        """Initialize test settings with default values."""
        test_values = {
            "environment": Environment.LOCAL,  # Use Environment enum directly
            "firecrawl_api_key": "test-key",
            "anthropic_api_key": "test-key",
            "openai_api_key": "test-key",
            "cohere_api_key": "test-key",
            "supabase_url": "https://test.supabase.co",
            "supabase_service_key": "test-key",
            "logfire_token": "test-key",
            "redis_url": "redis://localhost:6379",
            "log_level": "DEBUG",
            "src_dir": Path(__file__).parent,
            "use_ngrok": False,
        }
        test_values.update(values)
        super().__init__(**test_values)
