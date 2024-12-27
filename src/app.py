import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import logfire
import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config.cors_config import get_cors_config
from src.api.handlers.error_handlers import global_exception_handler, non_retryable_exception_handler
from src.api.middleware.debug_middleware import RequestDebugMiddleware
from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.system.health import router as health_router
from src.api.system.sentry_debug import router as sentry_debug_router
from src.api.v0.endpoints.chat import chat_router, conversations_router
from src.api.v0.endpoints.sources import router as content_router
from src.api.v0.endpoints.webhooks import router as webhook_router
from src.core._exceptions import NonRetryableError
from src.infra.logger import configure_logging, get_logger
from src.infra.service_container import ServiceContainer
from src.infra.settings import Environment, settings

# Configure logging
DEBUG = settings.log_level == "debug"
configure_logging(debug=DEBUG)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    container = None  # Initialize container to None
    try:
        # 1. Start external dependencies for local development
        if settings.environment == Environment.LOCAL:
            subprocess.run(["make", "up"])

        # 2. Initialize services
        container = await ServiceContainer.create()

        # 3. Save app state
        app.state.container = container
        yield
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise
    finally:
        if settings.environment == Environment.LOCAL and container:  # Check if container is not None
            subprocess.run(["make", "down"])
            await container.shutdown_services()


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
        description="RAG-powered LLM chat application",
        lifespan=lifespan,
    )

    # instrument with logfire
    logfire.configure(
        token=settings.logfire_write_token,
        environment=settings.environment,
        service_name=settings.project_name,
    )
    logfire.instrument_fastapi(app)
    logfire.instrument_httpx()
    logfire.instrument_asyncpg()
    logfire.instrument_redis()

    # Add middleware
    app.add_middleware(RequestDebugMiddleware)
    app.add_middleware(CORSMiddleware, **get_cors_config(settings.environment))
    app.add_middleware(HealthCheckRateLimit, requests_per_minute=60)

    # Add routes
    app.include_router(health_router, tags=["system"])
    app.include_router(sentry_debug_router, tags=["system"])
    app.include_router(webhook_router, tags=["webhooks"])
    app.include_router(content_router, tags=["content"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(conversations_router, tags=["chat"])

    # Add exception handlers
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(NonRetryableError, non_retryable_exception_handler)

    return app


def run() -> None:
    """Run the FastAPI application."""
    try:
        logger.info(
            f"Starting Kollektiv API on {settings.api_host}:{settings.api_port} environment: {settings.environment.value}"
        )
        app = create_app()
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down server...")


if __name__ == "__main__":
    run()
