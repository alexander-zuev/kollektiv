import logging
import os

from colorama import Fore, Style, init

from src.utils.config import LOG_DIR

# Initialize colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.LIGHTCYAN_EX,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    EMOJIS = {
        logging.DEBUG: "🐞",  # Debug
        logging.INFO: "ℹ️",  # Info
        logging.WARNING: "⚠️",  # Warning
        logging.ERROR: "❌",  # Error
        logging.CRITICAL: "🔥",  # Critical
    }

    def format(self, record):
        # Get the original log message
        log_message = super().format(record)

        # Get the color and emoji based on the log level
        color = self.COLORS.get(record.levelno, "")
        emoji = self.EMOJIS.get(record.levelno, "")

        # Construct the final log message with emoji before the log level
        log_message = f"{emoji} {record.levelname} - {log_message}"

        return f"{color}{log_message}{Style.RESET_ALL}"


def configure_logging(debug=False, log_file="app.log"):
    """
    Configures the logging system.

    Parameters:
    - debug (bool): If True, sets the logging level to DEBUG.
    - log_file (str): The name of the log file.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    app_logger = logging.getLogger("omni-claude")
    app_logger.setLevel(log_level)

    # Remove existing handlers to prevent duplication
    if app_logger.handlers:
        app_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter("%(asctime)s - %(name)s:%(lineno)d - %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler
    log_file_path = os.path.join(LOG_DIR, log_file)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file
    file_formatter = logging.Formatter("%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Add handlers to the root logger
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)


def get_logger():
    """
    Retrieves a logger with the 'omni-claude' prefix based on the caller's module.
    """
    import inspect

    frame = inspect.currentframe()
    try:
        # Get the frame of the caller
        caller_frame = frame.f_back
        module = inspect.getmodule(caller_frame)
        module_name = module.__name__ if module else "omni-claude"
    finally:
        del frame  # Prevent reference cycles

    return logging.getLogger(f"omni-claude.{module_name}")
