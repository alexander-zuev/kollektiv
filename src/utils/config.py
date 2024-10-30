import os
from enum import Enum
from typing import Final

from dotenv import load_dotenv

load_dotenv()


# Environment
class Environment(str, Enum):
    """Environment types."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


ENVIRONMENT: Final = Environment(os.getenv("ENVIRONMENT", Environment.LOCAL))

# Base URLs
BASE_URL = {
    Environment.LOCAL: "http://localhost:8000",
    Environment.STAGING: "https://staging.yourdomain.com",
    Environment.PRODUCTION: "https://yourdomain.com",
}[ENVIRONMENT]

# FireCrawl Configuration
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"

# Crawler Configuration
MAX_RETRIES: Final = 3
BACKOFF_FACTOR: Final = 2
DEFAULT_PAGE_LIMIT: Final = 25
DEFAULT_MAX_DEPTH: Final = 5

# Webhook Configuration
WEBHOOK_PATH: Final = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Fallback to local URL if not set
if not WEBHOOK_URL:
    WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")
WEAVE_PROJECT_NAME = os.getenv("WEAVE_PROJECT_NAME")

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_ROOT = os.path.join(BASE_DIR, "src")
LOG_DIR = os.path.join(BASE_DIR, "logs")
EVAL_DIR = os.path.join(BASE_DIR, "src", "evaluation")
JOB_FILE_DIR = os.path.join(BASE_DIR, "src", "crawling")
RAW_DATA_DIR = os.path.join(BASE_DIR, "src", "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "src", "data", "chunks")
CHROMA_DB_DIR = os.path.join(SRC_ROOT, "vector_storage", "chroma")
VECTOR_STORAGE_DIR = os.path.join(SRC_ROOT, "vector_storage")

# LLM config
MAIN_MODEL = "claude-3-5-sonnet-20241022"

# Evaluation config
EVALUATOR_MODEL_NAME = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"


# Ensure directories exist
os.makedirs(JOB_FILE_DIR, exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
os.makedirs(VECTOR_STORAGE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


class Config:
    """Configuration settings for the application.

    This class manages all configuration settings and environment variables
    used throughout the application.
    """
