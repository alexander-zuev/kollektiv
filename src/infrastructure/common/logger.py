import logging
import sys
from enum import Enum

import logfire
from colorama import Fore, Style, init

from src.infrastructure.config.settings import Environment, settings

# Initialize colorama
init(autoreset=True)

# Configure logfire with your settings


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
        # Color for interpolated values in messages
    }

    SYMBOLS = {
        logging.INFO: LogSymbols.INFO.value,  # Info
        logging.DEBUG: LogSymbols.DEBUG.value,  # Debug
        logging.WARNING: LogSymbols.WARNING.value,  # Warning
        logging.ERROR: LogSymbols.ERROR.value,  # Error
        logging.CRITICAL: LogSymbols.CRITICAL.value,  # Critical
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


def configure_logging(debug: bool = False) -> None:
    """Configure the application's logging system with both local handlers and Logfire."""
    # Setup log level
    log_level = logging.DEBUG if debug else logging.INFO

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
        logfire.configure(
            token=settings.logfire_write_token,
            environment=settings.environment,
            service_name=settings.project_name,
        )
        logfire_handler = logfire.LogfireLoggingHandler()
        app_logger.addHandler(logfire_handler)

    # 4. Control FastAPI logging
    for logger_name in ["uvicorn", "uvicorn.access"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # 5. Propagate to other loggers
    app_logger.propagate = False


def get_logger() -> logging.Logger:
    """
    Retrieve a logger named after the calling module.

    Returns:
        logging.Logger: A logger specifically named for the module calling the function.

    Raises:
        None
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

    return logging.getLogger(f"kollektiv.{module_name}")
