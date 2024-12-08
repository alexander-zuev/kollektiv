import logging
import os
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.api.routes import Routes

# Simple logger just for settings initialization
logger = logging.getLogger("kollektiv.settings")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(handler)


class Environment(str, Enum):
    """Supported application environments."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application-wide settings."""

    # General
    project_name: str = Field("kollektiv", description="Project name")

    # Environment configuration
    environment: Environment = Field(Environment.LOCAL, alias="ENVIRONMENT", description="Application environment")

    # API keys
    firecrawl_api_url: str = Field("https://api.firecrawl.dev/v1", description="Firecrawl API URL")
    firecrawl_api_key: str = Field(..., alias="FIRECRAWL_API_KEY")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    cohere_api_key: str = Field(..., alias="COHERE_API_KEY")
    weave_project_name: str | None = Field(None, alias="WEAVE_PROJECT_NAME")

    # Server configuration
    api_host: str = Field(
        "127.0.0.1" if Environment.LOCAL else "0.0.0.0",  # Local uses localhost, others use 0.0.0.0
        alias="API_HOST",
        description="API host - 127.0.0.1 for local, 0.0.0.0 for staging/prod",
    )
    api_port: int = Field(
        default=8000,
        alias="PORT",  # Railway injects PORT environment variable
        description="API port - defaults to 8000, but can be overridden by Railway's PORT variable",
    )
    chainlit_host: str = Field("127.0.0.1", description="Chainlit host")
    chainlit_port: int = Field(8001, description="Chainlit port")
    log_level: str = Field("debug", description="Logging level")

    # Crawler configuration
    max_retries: int = Field(3, description="Maximum retries for crawler requests")
    backoff_factor: float = Field(2.0, description="Backoff factor for retries")
    default_page_limit: int = Field(25, description="Default page limit for crawls")
    default_max_depth: int = Field(5, description="Default max depth for crawls")

    # LLM configuration
    main_model: str = Field("claude-3-5-sonnet-20241022", description="Main LLM model")
    evaluator_model_name: str = Field("gpt-4o-mini", description="Evaluator model name")
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")

    # Base directory is src/
    src_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    # Supabase
    supabase_url: str = Field(..., description="Supabase URL", alias="SUPABASE_URL")
    supabase_key: str = Field(..., description="Supabase Service Key", alias="SUPABASE_SERVICE_KEY")

    # All paths are now relative to src_dir
    log_dir: Path = Field(default_factory=lambda: Path("src/logs"))
    eval_dir: Path = Field(default_factory=lambda: Path("src/core/evaluation"))
    raw_data_dir: Path = Field(default_factory=lambda: Path("src/data/raw"))
    processed_data_dir: Path = Field(default_factory=lambda: Path("src/data/processed"))
    job_file_dir: Path = Field(default_factory=lambda: Path("src/core/content/crawler"))
    vector_storage_dir: Path = Field(default_factory=lambda: Path("src/infrastructure/storage/vector"))
    chroma_db_dir: Path = Field(default_factory=lambda: Path("src/infrastructure/storage/vector/chroma"))

    # Ngrok configuration (only for local development)
    use_ngrok: bool = Field(True, description="Whether to use ngrok in local development")
    ngrok_auth_token: str | None = Field(None, alias="NGROK_AUTH_TOKEN")
    _ngrok_url: str | None = None

    # Monitoring
    logfire_write_token: str = Field(..., alias="LOGFIRE_TOKEN", description="Logfire write token")
    sentry_dsn: str = Field(
        "https://c2f1acc0646d1578b572e318b6b118d5@o4508393623257088.ingest.us.sentry.io/4508393650847744",
        alias="SENTRY_DSN",
        description="Sentry DSN",
    )

    # Redis
    redis_url: str = Field(..., alias="REDIS_URL", description="Redis URL")

    model_config = SettingsConfigDict(
        env_file=os.path.join("config", "environments", ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def base_url(self) -> str:
        """Dynamically generate base URL based on environment."""
        if self.environment == Environment.LOCAL:
            if self.use_ngrok and self._ngrok_url:
                return self._ngrok_url
            return f"http://{self.api_host}:{self.api_port}"

        base_url = os.getenv("BASE_URL")
        if not base_url:
            raise ValueError(f"BASE_URL environment variable is required for {self.environment} environment")
        return base_url

    @property
    def firecrawl_webhook_url(self) -> str:
        """Dynamically generates the Firecrawl webhook URL."""
        return f"{self.base_url}{Routes.System.Webhooks.FIRECRAWL}"

    def setup_ngrok(self) -> None:
        """Initialize ngrok tunnel if in local environment."""
        if self.environment != Environment.LOCAL or not self.use_ngrok:
            return

        try:
            from pyngrok import conf, ngrok

            if self.ngrok_auth_token:
                conf.get_default().auth_token = self.ngrok_auth_token

            # Use api_port directly instead of ngrok_port
            tunnel = ngrok.connect(self.api_port, bind_tls=True)
            self._ngrok_url = tunnel.public_url
            logger.info(f"Ngrok tunnel established at {self._ngrok_url}")

        except ImportError:
            logger.warning("pyngrok not installed. Ngrok integration disabled.")
            self.use_ngrok = False
        except Exception as e:
            logger.error(f"Failed to initialize ngrok: {str(e)}")
            self.use_ngrok = False


# Initialize settings instance
try:
    settings = Settings()
    logger.info("Settings initialized successfully.")

    # Create directories
    for dir_path in [
        settings.log_dir,
        settings.raw_data_dir,
        settings.processed_data_dir,
        settings.chroma_db_dir,
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)

except ValueError as e:
    logger.error("Environment variables not set.")
    raise ValueError(f"An error occurred during settings loading: {str(e)}") from e
except Exception as e:
    logger.error("Error occurred while loading settings")
    raise Exception(f"An error occurred during settings loading: {str(e)}") from e
