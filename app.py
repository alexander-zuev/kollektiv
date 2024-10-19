import chainlit as cl

from src.core.component_initializer import ComponentInitializer
from src.ui.terminal_ui import run_terminal_ui
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


@base_error_handler
def setup_chainlit():
    """
    Set up and initialize the Chainlit environment.

    Args:
        None

    Returns:
        ClaudeAssistant: An instance of the ClaudeAssistant initialized with the specified documents.

    Raises:
        BaseError: If there is an error during the initialization process.
    """
    docs = [
        "docs_anthropic_com_en_20240928_135426-chunked.json",
        "langchain-ai_github_io_langgraph_20240928_210913-chunked.json",
    ]
    initializer = ComponentInitializer(reset_db=False, load_all_docs=False, files=docs)
    claude_assistant = initializer.init()
    return claude_assistant


@base_error_handler
def main(debug: bool = False, reset_db: bool = False):
    """
    Execute the main functionality of the script.

    Args:
        debug (bool): Defines if debug mode should be enabled.
        reset_db (bool): Indicates whether the database should be reset.

    Returns:
        None
    """
    # Configure logging before importing other modules
    configure_logging(debug=debug)

    # Initialize components
    claude_assistant = setup_chainlit()
    run_terminal_ui(claude_assistant)


# Initialize the assistant when the Chainlit app starts
assistant = setup_chainlit()


@cl.on_chat_start
async def on_chat_start():
    """
    Handle the chat start event and send initial welcome messages.

    Args:
        None

    Returns:
        None
    """
    await cl.Message(content="Hello! I'm Kollektiv, sync any web content and let's chat!").send()


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle an incoming message from the CL framework.

    Args:
        message (cl.Message): The message object containing the user's input.

    Returns:
        None
    """
    if assistant is None:
        logger.error("Assistant instance is not initialized.")
        await cl.Message(content="Error: Assistant is not initialized.").send()
        return

    response = assistant.get_response(user_input=message.content, stream=True)

    current_message = cl.Message(content="")
    await current_message.send()

    tool_used = False

    for event in response:
        if event["type"] == "text":
            if tool_used:
                # If a tool was used, start a new message for the assistant's response
                current_message = cl.Message(content="")
                await current_message.send()
                tool_used = False
            await current_message.stream_token(event["content"])
        elif event["type"] == "tool_use":
            tool_name = event.get("tool", "Unknown tool")
            await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
            tool_used = True

    await current_message.update()


if __name__ == "__main__":
    main(debug=False, reset_db=False)
