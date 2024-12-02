from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import logfire
import sentry_sdk
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.system.health import router as health_router
from src.api.system.sentry_debug import router as sentry_debug_router
from src.api.v0.endpoints.sources import router as content_router
from src.api.v0.endpoints.webhooks import router as webhook_router
from src.core._exceptions import NonRetryableError
from src.infrastructure.common.logger import configure_logging, get_logger
from src.infrastructure.config.settings import Environment, settings
from src.infrastructure.service_container import ServiceContainer

# Configure logging
DEBUG = settings.log_level == "debug"
configure_logging(debug=DEBUG)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Kollektiv API...")
    try:
        # Initialize ngrok for local development
        if settings.environment == Environment.LOCAL:
            settings.setup_ngrok()

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
        if settings.environment == Environment.LOCAL and settings.use_ngrok:
            from pyngrok import ngrok

            ngrok.kill()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=1,  # capture 100% of transactions
        _experiments={"continuous_profiling_auto_start": True},
        environment=settings.environment.value,
    )

    app = FastAPI(
        title="Kollektiv API",
        description="RAG-powered documentation chat application",
        lifespan=lifespan,
    )

    # instrument with logfire
    logfire.instrument_fastapi(app)

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
    app.include_router(sentry_debug_router, tags=["system"])
    app.include_router(webhook_router, tags=["webhooks"])
    app.include_router(content_router, tags=["content"])

    # Add global exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Global exception handler for any unhandled exceptions."""
        logger.critical(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"detail": "An internal server error occurred, please contact support."}
        )

    # Specific unretryable exception handlers
    @app.exception_handler(NonRetryableError)
    async def non_retryable_exception_handler(request: Request, exc: NonRetryableError) -> JSONResponse:
        """Catch and log a non-retryable error."""
        logger.error(f"Non-retryable error at {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal error occured while processing your request: {str(exc)}."},
        )

    return app


def run() -> None:
    """Run the FastAPI application."""
    # Security warnings for non-localhost bindings
    if settings.api_host != "127.0.0.1":
        logger.warning(
            "Warning: API server is binding to a non-localhost address. "
            "Make sure this is intended for production use."
        )

    try:
        logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
        app = create_app()
        uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level=settings.log_level)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        logger.info("Server shut down successfully")


if __name__ == "__main__":
    run()
