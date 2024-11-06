import os
from enum import Enum
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


# Environment
class Environment(str, Enum):
    """Environment types."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


ENVIRONMENT: Final = Environment(os.getenv("ENVIRONMENT", Environment.LOCAL))


def get_env_file_path(environment: Environment) -> Path | None:
    env_file_path = Path(f"config/environments/.env.{environment.value}")
    if os.getenv("CI"):  # set in GitHub Actions
        return None
    if not env_file_path.exists():
        raise FileNotFoundError(
            f"Environment file not found: {env_file_path}"
            f"Please ensure the file exists in the config/environments directory and is named correctly."
        )
    return env_file_path


env_file_path = get_env_file_path(ENVIRONMENT)
if env_file_path is not None and env_file_path.exists():
    load_dotenv(dotenv_path=env_file_path)


# Server Configuration
API_HOST: Final = os.getenv("API_HOST", "127.0.0.1")
API_PORT: Final = int(os.getenv("API_PORT", "8000"))
CHAINLIT_HOST: Final = os.getenv("CHAINLIT_HOST", "127.0.0.1")
CHAINLIT_PORT: Final = int(os.getenv("CHAINLIT_PORT", "8001"))
LOG_LEVEL: Final = os.getenv("LOG_LEVEL", "debug")

# Base URLs
BASE_URL = {
    Environment.LOCAL: f"http://localhost:{API_PORT}",
    Environment.STAGING: "https://staging.yourdomain.com",
    Environment.PRODUCTION: "https://yourdomain.com",
}[ENVIRONMENT]

# FireCrawl Configuration
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"

# Webhook Configuration
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", BASE_URL)  # Sets to ngrok host if available

# Crawler Configuration
MAX_RETRIES: Final = 3
BACKOFF_FACTOR: Final = 2
DEFAULT_PAGE_LIMIT: Final = 25
DEFAULT_MAX_DEPTH: Final = 5

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")
WEAVE_PROJECT_NAME = os.getenv("WEAVE_PROJECT_NAME")

# LLM Configuration
MAIN_MODEL = "claude-3-5-sonnet-20241022"
EVALUATOR_MODEL_NAME = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # Go up one more level
SRC_ROOT = os.path.join(BASE_DIR, "src")

# Core directories
LOG_DIR = os.path.join(BASE_DIR, "logs")  # Keep logs at project root
EVAL_DIR = os.path.join(SRC_ROOT, "evaluation")  # Keep evaluation in src

# Content directories
RAW_DATA_DIR = os.path.join(SRC_ROOT, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(SRC_ROOT, "data", "chunks")
JOB_FILE_DIR = os.path.join(SRC_ROOT, "core", "content", "crawler")  # Keep original structure

# Infrastructure directories
VECTOR_STORAGE_DIR = os.path.join(SRC_ROOT, "infrastructure", "storage", "vector")  # Keep original structure
CHROMA_DB_DIR = os.path.join(VECTOR_STORAGE_DIR, "chroma")

# Ensure critical directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)


def validate_required_env_vars() -> None:
    """Validate that all required environment variables are set."""
    required_vars = {
        "FIRECRAWL_API_KEY": FIRECRAWL_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        # Add other required variables
    }

    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise OSError(f"Missing required environment variables: {', '.join(missing_vars)}")


# Add this after all environment variables are loaded
if ENVIRONMENT != Environment.LOCAL:  # Only validate in non-local environments
    validate_required_env_vars()
