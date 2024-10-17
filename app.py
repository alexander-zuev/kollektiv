from src.core.component_initializer import ComponentInitializer
from src.ui.chainlit_ui import run_chainlit
from src.ui.terminal_ui import run_terminal_ui
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging


@base_error_handler
def main(debug: bool = False, reset_db: bool = False, interface: str = "terminal"):
    # Configure logging before importing other modules
    configure_logging(debug=debug)

    # TODO: allow users to select documents locally or pull from a db
    docs = [
        "docs_anthropic_com_en_20240928_135426-chunked.json",
        "langchain-ai_github_io_langgraph_20240928_210913-chunked.json",
        # "docs_ragas_io_en_stable_20241015_112520-chunked.json",
    ]

    # Initialize components
    initializer = ComponentInitializer(reset_db=reset_db, load_all_docs=False, files=docs)
    claude_assistant = initializer.init()

    if interface == "web":
        run_chainlit(claude_assistant)
    else:
        run_terminal_ui(claude_assistant)


if __name__ == "__main__":
    # TODO: reset DB should be a command a user can use
    main(debug=False, reset_db=False, interface="web")
