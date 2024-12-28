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
from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.system.health import router as health_router
from src.api.system.sentry_debug import router as sentry_debug_router
from src.api.v0.endpoints.chat import chat_router, conversations_router
from src.api.v0.endpoints.sources import router as content_router
from src.api.v0.endpoints.webhooks import router as webhook_router
from src.infra.logger import configure_logging, get_logger
from src.infra.service_container import ServiceContainer
from src.infra.settings import Environment, settings


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
    except Exception:
        logfire.exception("Failed to start Kollektiv!")
        raise
    finally:
        if settings.environment == Environment.LOCAL and container:  # Check if container is not None
            subprocess.run(["make", "down"])
            await container.shutdown_services()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure standard logging first
    configure_logging(debug=settings.debug)
    logger = get_logger()

    # Initialize Sentry
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
        redoc_url="/redoc",
    )

    # Add middleware
    app.add_middleware(CORSMiddleware, **get_cors_config(settings.environment))
    app.add_middleware(HealthCheckRateLimit, requests_per_minute=60)

    # Add routes
    app.include_router(health_router, tags=["system"])
    app.include_router(sentry_debug_router, tags=["system"])
    app.include_router(webhook_router, tags=["webhooks"])
    app.include_router(content_router, tags=["sources"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(conversations_router, tags=["chat"])

    # Add exception handlers
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(Exception, non_retryable_exception_handler)

    return app


def run() -> None:
    """Run the FastAPI application."""
    try:
        uvicorn.run(
            app=create_app(),
            host=settings.api_host,
            port=settings.api_port,
            log_level="debug" if settings.debug else "info",
        )
    except KeyboardInterrupt:
        raise


if __name__ == "__main__":
    run()
