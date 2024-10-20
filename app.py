import os

import chainlit as cl

from src.crawling.crawler import FireCrawler
from src.generation.summary_manager import SummaryManager
from src.interface.command_handler import CommandHandler
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


# TODO: the files should not be hardcoded but persisted properly. Right now this is very brittle
# TODO: the database should initialize with existing documents
# TODO: there has to be a way to re-index / update a particular content
@base_error_handler
def initialize_kollektiv():
    """
    Set up Kollektiv backend for the UI (Chainlit).

    Args:
        None

    Returns:
        ClaudeAssistant: An instance of the ClaudeAssistant initialized with the specified documents.

    Raises:
        BaseError: If there is an error during the initialization process.
    """
    logger.info("Initializing Kollektiv...")
    docs_to_load = [f for f in os.listdir(PROCESSED_DATA_DIR) if os.path.isfile(os.path.join(PROCESSED_DATA_DIR, f))]
    # Initialize components
    crawler = FireCrawler()
    chunker = MarkdownChunker()
    vector_db = VectorDB()
    summarizer = SummaryManager()

    kollektiv = Kollektiv(
        crawler=crawler,
        chunker=chunker,
        vector_db=vector_db,
        summarizer=summarizer,
        reset_db=False,
        load_all_docs=False,
        files=docs_to_load,
    )

    claude_assistant = kollektiv.init()
    command_handler = CommandHandler(kollektiv)
    message_handler = MessageHandler(claude_assistant, command_handler)
    return message_handler


# @base_error_handler
# def main(debug: bool = False, reset_db: bool = False):
#     """
#     Execute the main functionality of the script.
#
#     Args:
#         debug (bool): Defines if debug mode should be enabled.
#         reset_db (bool): Indicates whether the database should be reset.
#
#     Returns:
#         None
#     """
#     # Configure logging before importing other modules
#     configure_logging(debug=debug)
#
#     # Initialize components
#     claude_assistant = initialize_kollektiv()
#     run_terminal_ui(claude_assistant)


# Initialize the assistant when the Chainlit app starts
# assistant = initialize_kollektiv()

# Initialize the message handler when the Chainlit app starts
message_handler = initialize_kollektiv()


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
    await message_handler.handle_message(message)
    # response = message_handler.get_response(user_input=message.content, stream=True)
    #
    # current_message = cl.Message(content="")
    # await current_message.send()
    #
    # tool_used = False
    #
    # for event in response:
    #     if event["type"] == "text":
    #         if tool_used:
    #             # If a tool was used, start a new message for the assistant's response
    #             current_message = cl.Message(content="")
    #             await current_message.send()
    #             tool_used = False
    #         await current_message.stream_token(event["content"])
    #     elif event["type"] == "tool_use":
    #         tool_name = event.get("tool", "Unknown tool")
    #         await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
    #         tool_used = True
    #
    # await current_message.update()


# if __name__ == "__main__":
#     main(debug=False, reset_db=False)
