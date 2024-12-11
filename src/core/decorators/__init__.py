"""Error handling decorators for the application."""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

import aiohttp
from anthropic import AnthropicError, RateLimitError

from src.core._exceptions import ConnectionError, StreamingError, TokenLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def base_error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """Base error handler for all operations."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise StreamingError(f"Error in {func.__name__}: {str(e)}") from e

    return wrapper


def anthropic_error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """Error handler for Anthropic API operations."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded in {func.__name__}: {str(e)}")
            raise TokenLimitError("Rate limit exceeded") from e
        except AnthropicError as e:
            logger.error(f"Anthropic API error in {func.__name__}: {str(e)}")
            raise StreamingError(f"Error in {func.__name__}: {str(e)}") from e
        except aiohttp.ClientError as e:
            logger.error(f"Connection error in {func.__name__}: {str(e)}")
            raise ConnectionError("Failed to connect to Anthropic API") from e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise StreamingError(f"Error in {func.__name__}: {str(e)}") from e

    return wrapper
