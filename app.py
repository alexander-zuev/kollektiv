from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.routes import Routes
from src.api.system.health.health_router import router as health_router
from src.api.system.webhooks.webhook_router import router as webhook_router
from src.api.v0.content.sources import router as content_router
from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.infrastructure.config.logger import configure_logging, get_logger
from src.infrastructure.config.settings import (
    API_HOST,
    API_PORT,
    JOB_FILE_DIR,
    LOG_LEVEL,
)
from src.services.content_service import ContentService

# Configure logging
DEBUG = LOG_LEVEL == "debug"
configure_logging(debug=DEBUG)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Kollektiv API...")
    try:
        # Initialize dependencies
        job_manager = JobManager(JOB_FILE_DIR)
        firecrawler = FireCrawler()
        content_service = ContentService(firecrawler, job_manager)

        # Store in app state for access in routes
        app.state.job_manager = job_manager
        app.state.content_service = content_service
        app.state.firecrawler = firecrawler

        logger.info("Core services initialized successfully")
        yield  # Hand over to the application
    except Exception as e:
        logger.error(f"Failed to initialize core services: {str(e)}")
        raise  # Re-raise the exception to prevent startup
    finally:
        logger.info("Shutting down Kollektiv API...")


# Create the FastAPI app
app = FastAPI(
    title="Kollektiv API",
    description="RAG-powered documentation chat application",
)

# Assign the lifespan context to the app's lifespan attribute
app.lifespan = lifespan  # Correctly associate lifespan here

# Add middleware and routes *after* the app is created with lifespan
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

# Content routes
app.include_router(content_router, prefix=Routes.V0.BASE, tags=["content"])


def run() -> None:
    """Run the FastAPI application."""
    # Security warnings for non-localhost bindings
    if API_HOST != "127.0.0.1":
        logger.warning(
            "Warning: API server is binding to a non-localhost address. "
            "Make sure this is intended for production use."
        )

    try:
        logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
        uvicorn.run(app, host=API_HOST, port=API_PORT, log_level=LOG_LEVEL)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        logger.info("Server shut down successfully")


if __name__ == "__main__":
    run()
