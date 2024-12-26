import json
import logging
import sys
from enum import Enum

import logfire
from colorama import Fore, Style, init

from src.infra.settings import Environment, settings

# Initialize colorama
init(autoreset=True)


class LogSymbols(str, Enum):
    """Unified symbols for all application logging."""

    SUCCESS = "✓"
    ERROR = "✗"
    INFO = "→"
    WARNING = "⚠"
    DEBUG = "•"
    CRITICAL = "‼"


class ColoredFormatter(logging.Formatter):
    """Enhance log messages with colors and emojis based on their severity levels."""

    COLORS = {
        logging.INFO: Fore.GREEN,
        logging.DEBUG: Fore.LIGHTCYAN_EX,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    SYMBOLS = {
        logging.INFO: LogSymbols.INFO.value,
        logging.DEBUG: LogSymbols.DEBUG.value,
        logging.WARNING: LogSymbols.WARNING.value,
        logging.ERROR: LogSymbols.ERROR.value,
        logging.CRITICAL: LogSymbols.CRITICAL.value,
    }
    VALUE_COLOR = Fore.LIGHTBLUE_EX

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colored level and symbol."""
        # Get timestamp and format module name more concisely
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        module = record.name.replace("kollektiv.src.", "")

        # Color both symbol and level
        color = self.COLORS.get(record.levelno, "")
        colored_symbol = f"{color}{self.SYMBOLS.get(record.levelno, '')}{Style.RESET_ALL}"
        colored_level = f"{color}{record.levelname}{Style.RESET_ALL}:"

        # Get formatted message directly
        message = record.getMessage()  # This handles all formatting

        # Final format
        return f"{colored_symbol} {colored_level} [{timestamp}] {module}: {message}"


class JsonFormatter(logging.Formatter):
    """Format the log record as a JSON structure."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON structure."""
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "line": record.lineno,
            "path": record.pathname,
        }
        # Add exception information if available
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        for key in dir(record):
            if not key.startswith("_") and key not in log_entry:
                log_entry[key] = getattr(record, key, None)
        return json.dumps(log_entry)


def configure_logging(debug: bool = False) -> None:
    """Configure the application's logging system with both local handlers and Logfire."""
    # Setup log level
    log_level = logging.DEBUG if debug else logging.INFO

    # 1. Configure Logfire first (in non-local)
    if settings.environment != Environment.LOCAL:
        try:
            logfire.configure(
                token=settings.logfire_write_token,
                environment=settings.environment,
                service_name=settings.project_name,
            )
        except Exception as e:
            print(f"Failed to configure Logfire: {e}")

    # 1. Configure kollektiv logger
    app_logger = logging.getLogger("kollektiv")
    app_logger.setLevel(log_level)
    app_logger.handlers.clear()

    # 2. Set up handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter("%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"))
    app_logger.addHandler(console_handler)

    # 3. Environment-specific handlers
    if settings.environment != Environment.LOCAL:
        logfire_handler = logfire.LogfireLoggingHandler()
        logfire_handler.setFormatter(JsonFormatter())
        app_logger.addHandler(logfire_handler)

    # 4. Add third-party logging handlers
    logging.getLogger("fastapi").setLevel(level=log_level)
    logging.getLogger("uvicorn.error").setLevel(level=log_level)
    logging.getLogger("docker").setLevel(level=log_level)
    logging.getLogger("wandb").setLevel(level=log_level)

    # 4. Propagate to other loggers
    app_logger.propagate = False


def get_logger() -> logging.LoggerAdapter:
    """
    Retrieve a logger named after the calling module.

    Returns:
        logging.LoggerAdapter: A logger adapter that supports extra context fields.
    """
    import inspect

    frame = inspect.currentframe()
    try:
        # Get the frame of the caller
        caller_frame = frame.f_back
        module = inspect.getmodule(caller_frame)
        module_name = module.__name__ if module else "kollektiv"
    finally:
        del frame  # Prevent reference cycles

    logger = logging.getLogger(f"kollektiv.{module_name}")
    return logging.LoggerAdapter(logger, extra={})
