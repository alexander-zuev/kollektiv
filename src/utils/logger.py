import logging
import os

from colorama import Fore, Style, init

from src.utils.config import LOG_DIR

# Initialize colorama
init(autoreset=True)

# Initialize default log level
LOG_LEVEL = logging.INFO


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "INFO": Fore.LIGHTCYAN_EX,  # Regular white for info
        "DEBUG": Fore.BLUE,  # Blue for debugging
        "WARNING": Fore.YELLOW,  # Yellow for warnings
        "ERROR": Fore.RED,  # Red for errors
        "CRITICAL": Fore.MAGENTA + Style.BRIGHT,  # Magenta and bright for critical issues
    }

    EMOJIS = {
        "INFO": "ℹ️",  # Information
        "DEBUG": "🐞",  # Debugging
        "WARNING": "⚠️",  # Warning
        "ERROR": "❌",  # Error
        "CRITICAL": "❗",  # Critical
    }

    def format(self, record):
        # Get the original log message
        log_message = super().format(record)

        # Get the color based on the log level
        color = self.COLORS.get(record.levelname, "")

        # Get the emoji based on the log level
        emoji = self.EMOJIS.get(record.levelname, "")

        # Construct the final log message with emoji and color
        return f"{color}{emoji} {log_message}{Style.RESET_ALL}"


def setup_logger(name: str, log_file: str, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False  # Prevent messages from being passed to ancestor loggers

    # Remove existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter("[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s")
    console_formatter = ColoredFormatter("[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(console_formatter)

    # Ensure LOG_DIR exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
    file_handler.setLevel(logging.DEBUG)  # Always log all levels to file
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def set_log_level(logger, level: int):
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(level)
