from fastapi import Request
from fastapi.responses import JSONResponse

from src.core._exceptions import NonRetryableError
from src.infra.logger import get_logger

logger = get_logger()


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for any unhandled exceptions."""
    logger.critical(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred, please contact support."}
    )


async def non_retryable_exception_handler(request: Request, exc: NonRetryableError) -> JSONResponse:
    """Catch and log a non-retryable error."""
    logger.error(f"Non-retryable error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"An internal error occured while processing your request: {str(exc)}."},
    )
