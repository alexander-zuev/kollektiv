import logging
import os

from colorama import Fore, Style, init

from src.utils.config import LOG_DIR

# Initialize colorama
init(autoreset=True)

# Initialize default log level
LOG_LEVEL = logging.INFO


class Logger:
    _instance = None

    @classmethod
    def initialize(cls, debug: bool = False, log_file: str = "app.log"):
        log_level = logging.DEBUG if debug else logging.INFO
        return cls.get_instance(log_level=log_level, log_file=log_file)

    @classmethod
    def get_instance(cls, log_level: int = logging.INFO, log_file: str = "app.log"):
        if cls._instance is None:
            cls._instance = cls(log_level, log_file)
        return cls._instance

    def __init__(self, log_level: int, log_file: str):
        if Logger._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Logger._instance = self
            self.root_logger = logging.getLogger()
            self.root_logger.setLevel(log_level)
            self.log_file = os.path.join(LOG_DIR, log_file)
            self._setup_handlers()

    def _setup_handlers(self):
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.root_logger.level)
        console_formatter = ColoredFormatter("[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log all levels to file
        file_formatter = logging.Formatter("[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s")
        file_handler.setFormatter(file_formatter)

        # Add handlers to the logger
        self.root_logger.addHandler(console_handler)
        self.root_logger.addHandler(file_handler)

    def set_log_level(self, level: int):
        self.root_logger.setLevel(level)
        for handler in self.root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def get_logger(self, name: str):
        return self.root_logger.getChild(name)

    def debug(self, msg, *args, **kwargs):
        self.root_logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.root_logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.root_logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.root_logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.root_logger.critical(msg, *args, **kwargs)


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


# Global logger instance
logger = Logger.initialize()
