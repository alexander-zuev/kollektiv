import multiprocessing
import sys
from contextlib import asynccontextmanager

import chainlit as cl
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.chainlit.message_handler import MessageHandler
from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.routes import Routes
from src.api.system.health.health_router import router as health_router
from src.api.system.webhooks.webhook_router import router as webhook_router
from src.core.system.job_manager import JobManager
from src.infrastructure.config.logger import configure_logging, get_logger
from src.infrastructure.config.settings import (
    API_HOST,
    API_PORT,
    CHAINLIT_HOST,
    CHAINLIT_PORT,
    JOB_FILE_DIR,
    LOG_LEVEL,
)
from src.services.manager import Kollektiv
from src.services.webhook_handler import WebhookHandler

# Configure logging
DEBUG = LOG_LEVEL == "debug"
configure_logging(debug=DEBUG)
logger = get_logger()

# Store the message handler globally (needed for Chainlit)
message_handler: "MessageHandler" = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info("Starting up Kollektiv API...")
    try:
        # Initialize core services according to system design
        job_manager = JobManager(JOB_FILE_DIR)
        webhook_handler = WebhookHandler(job_manager)

        # Store in app state for access in routes
        app.state.job_manager = job_manager
        app.state.webhook_handler = webhook_handler

        logger.info("Core services initialized successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize core services: {str(e)}")
        raise
    finally:
        logger.info("Shutting down Kollektiv API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Kollektiv API",
        description="RAG-powered documentation chat application",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting for health endpoint
    app.add_middleware(HealthCheckRateLimit, requests_per_minute=60)

    # System routes
    app.include_router(health_router, tags=["system"])
    app.include_router(webhook_router, prefix=Routes.System.Webhooks.BASE, tags=["system"])

    return app


# Chainlit handlers
@cl.on_chat_start
async def on_chat_start():
    """Handle the chat start event and send initial welcome messages."""
    global message_handler
    message_handler = await Kollektiv.setup(reset_db=True, load_all_docs=True)

    await cl.Message(
        content="Welcome to **Kollektiv**. I'm ready to assist you with web content management "
        "and answering your questions."
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Passes user message to MessageHandler for processing."""
    global message_handler
    await message_handler.route_message(message)


def run_api():
    """Run the FastAPI application."""
    app = create_app()
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level=LOG_LEVEL)


def run_chainlit():
    """Run the Chainlit application."""
    import os
    import subprocess

    os.environ["CHAINLIT_HOST"] = CHAINLIT_HOST
    os.environ["CHAINLIT_PORT"] = str(CHAINLIT_PORT)

    # Run chainlit as a subprocess
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "chainlit", "run", "app.py", "--host", CHAINLIT_HOST, "--port", str(CHAINLIT_PORT)],
        check=True,
        text=True,
        shell=False,  # Explicitly disable shell execution
    )
    # subprocess.run(["chainlit", "run", "main.py", "--host", CHAINLIT_HOST, "--port", str(CHAINLIT_PORT)])


def run():
    """Run both API and Chainlit servers."""
    # Security warnings for non-localhost bindings
    if API_HOST != "127.0.0.1":
        logger.warning(
            "Warning: API server is binding to a non-localhost address. "
            "Make sure this is intended for production use."
        )
    if CHAINLIT_HOST != "127.0.0.1":
        logger.warning(
            "Warning: Chainlit server is binding to a non-localhost address. "
            "Make sure this is intended for production use."
        )

    api_process = multiprocessing.Process(target=run_api, name="API")
    chat_process = multiprocessing.Process(target=run_chainlit, name="Chainlit")

    try:
        logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
        api_process.start()

        logger.info(f"Starting Chainlit UI on {CHAINLIT_HOST}:{CHAINLIT_PORT}")
        chat_process.start()

        api_process.join()
        chat_process.join()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
        api_process.terminate()
        chat_process.terminate()
        api_process.join()
        chat_process.join()
        logger.info("Servers shut down successfully")


if __name__ == "__main__":
    run()
