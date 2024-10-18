import chainlit as cl

from src.core.component_initializer import ComponentInitializer
from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger

logger = get_logger()


# Initialize the assistant
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
        # "docs_ragas_io_en_stable_20241015_112520-chunked.json",
    ]
    # Initialize components
    initializer = ComponentInitializer(reset_db=False, load_all_docs=False, files=docs)
    claude_assistant = initializer.init()
    return claude_assistant


# Initialize the assistant when the Chainlit app starts
claude_assistant = setup_chainlit()


@cl.on_message
async def handle_message(message: str):
    """
    Handle the incoming message and generate an appropriate response.

    Args:
        message (str): The message received that needs to be processed.

    Returns:
        None

    Raises:
        None
    """
    if claude_assistant is None:
        logger.error("Assistant instance is not initialized.")
        await cl.Message(content="Error: Assistant is not initialized.").send()
        return

    logger.info(f"Received message: {message}")
    stream = True
    response = claude_assistant.get_response(message, stream=stream)

    if stream:
        async for event in response:
            if event["type"] == "text":
                await cl.Message(content=event["content"]).send()
            elif event["type"] == "tool_use":
                tool_name = event.get("tool", "Unknown tool")
                await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
    else:
        await cl.Message(content=response).send()
