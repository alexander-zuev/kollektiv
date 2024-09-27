from src.core.component_initializer import ComponentInitializer
from src.ui.terminal_ui import run_terminal_ui
from src.utils.decorators import application_level_handler
from src.utils.logger import configure_logging


@application_level_handler
def main(debug: bool = False, reset_db: bool = False):
    # Configure logging before importing other modules
    configure_logging(debug=debug)

    # Initialize components
    initializer = ComponentInitializer()
    claude_assistant = initializer.initialize(reset_db=reset_db)

    run_terminal_ui(claude_assistant)


if __name__ == "__main__":
    main(debug=True, reset_db=False)  # Set debug=True to enable debug logging
