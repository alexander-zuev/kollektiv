import logging
import os
import sys

from colorama import Fore, Style, init

from src.infrastructure.config.settings import settings

# Initialize colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Enhance log messages with colors and emojis based on their severity levels.

    Args:
        logging (module): A logging module instance for handling logs.

    Returns:
        None

    Raises:
        KeyError: If a log level is not found in COLORS or EMOJIS dictionaries.
    """

    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.LIGHTCYAN_EX,
        logging.WARNING: Fore.LIGHTYELLOW_EX,
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

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with emoji and color based on log level.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message including color and emoji.

        Raises:
            KeyError: If a log level key does not exist in COLORS or EMOJIS.

        """
        # Get the original log message
        log_message = super().format(record)

        # Get the color and emoji based on the log level
        color = self.COLORS.get(record.levelno, "")
        emoji = self.EMOJIS.get(record.levelno, "")

        # Construct the final log message with emoji before the log level
        log_message = f"{emoji} {record.levelname} - {log_message}"

        return f"{color}{log_message}{Style.RESET_ALL}"


def configure_logging(debug: bool = False, log_file: str = "app.log") -> None:
    """
    Configure the application's logging system.

    Args:
        debug (bool): Whether to set the logging level to debug. Defaults to False.
        log_file (str): The name of the file to log to. Defaults to "app.log".

    Returns:
        None

    Raises:
        Exception: Any exception that logging handlers or the file system might raise.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    app_logger = logging.getLogger("kollektiv")
    app_logger.setLevel(log_level)

    # Remove existing handlers to prevent duplication
    if app_logger.handlers:
        app_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter("%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler
    log_file_path = os.path.join(settings.log_dir, log_file)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file
    file_formatter = logging.Formatter("%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Add handlers to the app logger
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)

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
