import json
import subprocess
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import logfire
import sentry_sdk
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.middleware.rate_limit import HealthCheckRateLimit
from src.api.system.health import router as health_router
from src.api.system.sentry_debug import router as sentry_debug_router
from src.api.v0.endpoints.chat import chat_router, conversations_router
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
    try:
        # Initialize external dependencies for local development
        if settings.environment == Environment.LOCAL:
            settings.setup_ngrok()
            subprocess.run(["docker-compose", "-f", "scripts/docker/docker-compose.yml", "up", "-d"])

        # Initialize services
        container = ServiceContainer()
        await container.initialize_services()

        # Save in app state
        app.state.container = container
        logger.info("✓ Initialized core services successfully")
        yield  # Hand over to the application
    except Exception as e:
        logger.error(f"Failed to initialize core services: {str(e)}", exc_info=True)
        raise  # Re-raise the exception to prevent startup
    finally:
        logger.info("Shutting down Kollektiv API...")
        if settings.environment == Environment.LOCAL and settings.use_ngrok:
            from pyngrok import ngrok

            ngrok.kill()
        if settings.environment == Environment.LOCAL:
            subprocess.run(["docker-compose", "-f", "scripts/external_deps/docker-compose.yml", "down"])


def get_allowed_origins() -> list[str]:
    """Get the allowed origins based on the environment."""
    if settings.environment == Environment.LOCAL:
        return ["*"]
    return [
        "https://thekollektiv.ai",  # Main domain
        "https://bountiful-truth-staging.up.railway.app",  # Railway frontend URL
        "https://bountiful-truth.railway.internal",  # Railway internal URL
    ]


# Add debug middleware
class RequestDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Debug middleware to log request details."""
        try:
            # Log detailed request info
            logger.debug(
                f"\n{'='*50}\n"
                f"REQUEST DETAILS:\n"
                f"Method: {request.method}\n"
                f"Path: {request.url.path}\n"
                f"Client: {request.client.host if request.client else 'Unknown'}\n"
                f"Headers: {json.dumps(dict(request.headers), indent=2)}\n"
                f"Environment: {settings.environment}"
            )

            # Get request body for POST/PUT requests
            if request.method in ["POST", "PUT"]:
                try:
                    body = await request.body()
                    if body:
                        logger.debug(f"Request Body: {body.decode()}")
                except Exception as e:
                    logger.debug(f"Could not read body: {str(e)}")

            # Process request
            response = await call_next(request)

            # Log response info
            logger.debug(f"\nRESPONSE DETAILS:\n" f"Status: {response.status_code}\n" f"{'='*50}")

            return response
        except Exception as e:
            logger.error(f"Error in debug middleware: {str(e)}")
            return await call_next(request)


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
    # Add debug middleware first
    app.add_middleware(RequestDebugMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],  # Be explicit about methods
        allow_headers=["*"],
    )

    # Add rate limiting for health endpoint
    app.add_middleware(HealthCheckRateLimit, requests_per_minute=60)

    # Add routes
    app.include_router(health_router, tags=["system"])
    app.include_router(sentry_debug_router, tags=["system"])
    app.include_router(webhook_router, tags=["webhooks"])
    app.include_router(content_router, tags=["content"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(conversations_router, tags=["chat"])

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
        logger.info(f"Starting Kollektiv API on {settings.api_host}:{settings.api_port}")
        logger.info(f"Environment: {settings.environment.value}")
        app = create_app()
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        logger.info("Server shut down successfully")


if __name__ == "__main__":
    run()
