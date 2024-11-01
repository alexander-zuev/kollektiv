import chainlit as cl

from src.kollektiv.manager import Kollektiv
from src.utils.logger import configure_logging, get_logger

DEBUG = False

# Configure logging at the start of the file
configure_logging(debug=DEBUG)
logger = get_logger()

# Store the message handler globally
message_handler = None


@cl.on_chat_start
async def on_chat_start():
    """Handle the chat start event and send initial welcome messages."""
    global message_handler
    # Initialize the application when chat starts
    message_handler = await Kollektiv.setup(reset_db=True, load_all_docs=True)

    await cl.Message(
        content="Welcome to **Kollektiv**. I'm ready to assist you with web content management "
        "and answering your questions."
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Passes user message to MessageHandler for processing."""
    global message_handler
    if message_handler:
        await message_handler.route_message(message)
    else:
        await cl.Message(content="System is not properly initialized. Please try restarting.").send()
