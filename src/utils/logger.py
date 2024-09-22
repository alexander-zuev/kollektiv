# src/utils/logger.py
import logging
import os

from colorama import Fore, Style

from src.utils.config import LOG_DIR

# Initialize default log level
LOG_LEVEL = logging.INFO


def set_log_level(level):
    """
    Sets the global log level for all loggers.

    :param level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    global LOG_LEVEL
    LOG_LEVEL = level


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, '')}{log_message}{Style.RESET_ALL}"


def setup_logger(name: str, log_file: str):
    """
    Sets up a logger with the specified name and log file, using the global LOG_LEVEL.

    :param name: Name of the logger.
    :param log_file: File to which logs will be written.
    :return: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid adding multiple handlers if the logger already has them
    if not logger.hasHandlers():
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
