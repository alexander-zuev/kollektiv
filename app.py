from src.core.component_initializer import ComponentInitializer
from src.ui.terminal_ui import run_terminal_ui
from src.utils.decorators import application_level_handler
from src.utils.logger import setup_logger

logger = setup_logger(__name__, "app.log")


@application_level_handler(logger)
def main():
    claude_assistant = ComponentInitializer().initialize()
    run_terminal_ui(claude_assistant)


if __name__ == "__main__":
    main()
