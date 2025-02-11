import inspect
import json
import logging
import sys
from enum import Enum

import logfire
from colorama import Fore, Style, init

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
        # Step 1: Compute message and time exactly like the source
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        # Step 2: Format our custom message
        timestamp = record.asctime if hasattr(record, "asctime") else self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        name = record.name
        lineno = record.lineno

        # Apply colors
        color = self.COLORS.get(record.levelno, "")
        colored_symbol = f"{color}{self.SYMBOLS.get(record.levelno, '')}{Style.RESET_ALL}"
        colored_level = f"{color}{record.levelname}{Style.RESET_ALL}:"

        # Format extra fields consistently
        extra_arg_str = ""
        if record.args:
            extra_arg_str = f"Args: {json.dumps(record.args, default=str)}"

        # Build our custom formatted message
        s = f"{colored_symbol} {colored_level} [{timestamp}] {name}:{lineno} - {record.message}. {extra_arg_str}"

        # Step 3: Handle exc_info and stack_info EXACTLY like the source
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)

        return s


def configure_logging(debug: bool = False) -> None:
    """Configure the application's logging system with both local handlers and Logfire."""
    from src.infra.settings import settings

    # Setup log level
    log_level = logging.DEBUG if debug else logging.INFO
    if settings.logfire_write_token:
        logfire.configure(
            token=settings.logfire_write_token,
            environment=settings.environment,
            service_name=settings.project_name,
            console=False,
        )

    # 1. Configure kollektiv logger
    app_logger = logging.getLogger("kollektiv")
    app_logger.setLevel(log_level)
    app_logger.handlers.clear()

    # 2. Set up handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter())
    app_logger.addHandler(console_handler)

    # 3. Environment-specific handlers
    logfire_handler = logfire.LogfireLoggingHandler()
    app_logger.addHandler(logfire_handler)

    # 4. Add third-party logging handlers and configure their levels
    logging.getLogger("fastapi").setLevel(level=log_level)
    logging.getLogger("uvicorn.error").setLevel(level=log_level)
    logging.getLogger("docker").setLevel(level=log_level)
    logging.getLogger("wandb").setLevel(level=log_level)

    # Set Chroma and its dependencies to WARNING to reduce noise
    logging.getLogger("chromadb").setLevel(level=logging.WARNING)
    logging.getLogger("chromadb.api").setLevel(level=logging.WARNING)
    logging.getLogger("chromadb.telemetry").setLevel(level=logging.WARNING)

    # 5. Propagate to other loggers
    app_logger.propagate = False


def get_logger() -> logging.LoggerAdapter:
    """Retrieve a logger named after the calling module.

    Returns:
        logging.LoggerAdapter: A logger adapter that supports extra context fields.
    """
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back
        module = inspect.getmodule(caller_frame)
        module_name = module.__name__ if module else "kollektiv"
    finally:
        del frame  # Prevent reference cycles

    logger = logging.getLogger(f"kollektiv.{module_name}")
    return logging.LoggerAdapter(logger, extra={})


def _truncate_message(message: str, max_length: int = 200) -> str:
    """Truncate long messages for logging."""
    if len(message) > max_length:
        return f"{message[:max_length]}..."
    return message
