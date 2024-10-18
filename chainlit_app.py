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

@cl.on_chat_start
async def on_chat_start():
    """
    Handle the chat start event and send initial welcome messages.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: If there is an issue with sending messages.
    """
    await cl.Message(
        content="Hello! I'm your AI assistant, knowledgeable about Anthropic and LangChain. How can I help you today?"
    ).send()

    # Optionally, you can send a message about the loaded documents
    # TODO: send a first message to let user know which documents it has access to.
    # loaded_docs = ", ".join([
    #     "Anthropic documentation",
    #     "LangChain LangGraph documentation"
    # ])
    # await cl.Message(
    #     content=f"I have information about the following documentation: {loaded_docs}. Feel free to ask me anything related to these topics!"
    # ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle an incoming message from the CL framework.

    Args:
        message (cl.Message): The message object containing the user's input.

    Returns:
        None

    Raises:
        RuntimeError: If the assistant instance is not initialized.
    """
    if claude_assistant is None:
        logger.error("Assistant instance is not initialized.")
        await cl.Message(content="Error: Assistant is not initialized.").send()
        return

    msg = cl.Message(content="")
    # await msg.send() # sends an empty message

    stream = True
    response = claude_assistant.get_response(user_input=message.content, stream=stream)

    for event in response:
        if event["type"] == "text":
            await msg.stream_token(event["content"])
        elif event["type"] == "tool_use":
            tool_name = event.get("tool", "Unknown tool")
            await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()

    await msg.update()