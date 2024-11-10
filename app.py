from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.system.health import router as health_router
from src.api.v0.endpoints.sources import router as content_router
from src.api.v0.endpoints.webhooks import router as webhook_router
from src.infrastructure.config.logger import configure_logging, get_logger
from src.infrastructure.config.settings import (
    API_HOST,
    API_PORT,
    LOG_LEVEL,
)
from src.infrastructure.service_container import ServiceContainer

# Configure logging
DEBUG = LOG_LEVEL == "debug"
configure_logging(debug=DEBUG)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Kollektiv API...")
    try:
        # Initialize services
        container = ServiceContainer()
        container.initialize_services()

        # Save in app state
        app.state.container = container
        logger.info("Core services initialized successfully")
        yield  # Hand over to the application
    except Exception as e:
        logger.error(f"Failed to initialize core services: {str(e)}")
        raise  # Re-raise the exception to prevent startup
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

    # Add routes
    app.include_router(health_router, tags=["system"])
    app.include_router(webhook_router, tags=["webhooks"])
    app.include_router(content_router, tags=["content"])

    return app


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
        app = create_app()
        uvicorn.run(app, host=API_HOST, port=API_PORT, log_level=LOG_LEVEL)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        logger.info("Server shut down successfully")


if __name__ == "__main__":
    run()
