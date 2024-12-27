import json
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class RequestDebugMiddleware(BaseHTTPMiddleware):
    """Debug middleware to log request details."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Dispatch the request."""
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

            # Process request
            response = await call_next(request)

            # Log response info
            logger.debug(f"\nRESPONSE DETAILS:\n" f"Status: {response.status_code}\n" f"{'='*50}")

            return response
        except Exception as e:
            logger.error(f"Error in debug middleware: {str(e)}")
            return await call_next(request)
