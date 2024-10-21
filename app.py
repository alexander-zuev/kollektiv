import os

import chainlit as cl

from src.crawling.crawler import FireCrawler
from src.generation.summary_manager import SummaryManager
from src.interface.command_handler import CommandHandler
from src.interface.flow_manager import FlowManager
from src.interface.message_handler import MessageHandler
from src.kollektiv.manager import Kollektiv
from src.processing.chunking import MarkdownChunker
from src.utils.config import PROCESSED_DATA_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger
from src.vector_storage.vector_db import VectorDB

DEBUG = False

# Configure logging at the start of the file
configure_logging(debug=DEBUG)
logger = get_logger()


@base_error_handler
def initialize_application():
    """
    Initializes the Kollektiv system and returns the MessageHandler.

    Args:
        None

    Returns:
        MessageHandler: An instance of the MessageHandler initialized with all components.

    Raises:
        BaseError: If there is an error during the initialization process.
    """
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