# src/utils/logger.py
import logging
import os

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
        # Create formatter
        formatter = logging.Formatter("[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_handler.setFormatter(formatter)

        # Ensure LOG_DIR exists
        os.makedirs(LOG_DIR, exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
