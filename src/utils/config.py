import os

from dotenv import load_dotenv

load_dotenv()

# FireCrawl Configuration
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# OpenAI API KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Cohere API Key
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_ROOT = os.path.join(BASE_DIR, "src")
LOG_DIR = os.path.join(BASE_DIR, "logs")
JOB_FILE_DIR = os.path.join(BASE_DIR, "src", "crawling")
RAW_DATA_DIR = os.path.join(BASE_DIR, "src", "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "src", "data", "chunks")

# Ensure directories exist
os.makedirs(JOB_FILE_DIR, exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
