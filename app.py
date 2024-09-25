import logging

from src.core.component_initializer import ComponentInitializer
from src.ui.terminal_ui import run_terminal_ui
from src.utils.decorators import application_level_handler
from src.utils.logger import logger


@application_level_handler()
def main(debug: bool = False):
    # Set log level based on debug mode
    log_level = logging.DEBUG if debug else logging.INFO
    logger.set_log_level(log_level)

    # Initialize components
    initializer = ComponentInitializer(debug=debug)
    claude_assistant = initializer.initialize()

    run_terminal_ui(claude_assistant)


if __name__ == "__main__":
    main(debug=False)  # Set debug to False for production
