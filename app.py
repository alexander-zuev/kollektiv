import chainlit as cl

from src.interface.message_handler import MessageHandler
from src.kollektiv.manager import Kollektiv
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

DEBUG = False

# Configure logging at the start of the file
configure_logging(debug=DEBUG)
logger = get_logger()


@base_error_handler
def initialize_application() -> MessageHandler:
    """Initializes the Kollektiv system and returns the MessageHandler."""
    return Kollektiv.setup(reset_db=False, load_all_docs=False)


message_handler = initialize_application()


@cl.on_chat_start
async def on_chat_start():
    """Handle the chat start event and send initial welcome messages."""
    await cl.Message(
        content="Welcome to **Kollektiv**. I'm ready to assist you with web content management "
        "and answering your questions."
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Passes user message to MessageHandler for processing."""
    await message_handler.route_message(message)
