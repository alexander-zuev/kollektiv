from src.core.component_initializer import ComponentInitializer
from src.ui.terminal_ui import run_terminal_ui


def main():
    claude_assistant = ComponentInitializer().initialize()
    run_terminal_ui(claude_assistant)


if __name__ == "__main__":
    main()
