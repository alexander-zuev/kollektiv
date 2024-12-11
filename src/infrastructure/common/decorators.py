import asyncio
import functools
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from anthropic import (
    AnthropicError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)

from src.core._exceptions import DatabaseError, NonRetryableLLMError, RetryableLLMError
from src.infrastructure.common.logger import get_logger

logger = get_logger()

P = ParamSpec("P")
T = TypeVar("T")


def base_error_handler(func: Callable[P, T]) -> Callable[P, T]:
    """Base async error handling decorator."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Create new error message instead of modifying LogRecord
            logger.error("Error in %s: %s", func.__name__, str(e))
            raise

    return wrapper


def generic_error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to catch and log any unhandled exceptions in a function."""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.critical(
                f"Unhandled exception in {func.__name__}: {str(e)}",
                exc_info=True,  # Include traceback in the log
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.critical(f"Unhandled exception in {func.__name__}: {str(e)}", exc_info=True)
            raise

    # Determine if the function is async or not
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def application_level_handler(func: Callable) -> Callable[..., T]:
    """Retrieve the application logger."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Access the logger
        logger = get_logger()

        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.info("User terminated program execution")
            sys.exit(0)
        except SystemExit:
            logger.info("\nSystem exit called")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise

    return wrapper


def anthropic_error_handler(func: Callable) -> Callable[..., T]:
    """
    Apply error handling for various exceptions encountered in Anthropic API calls.

    Args:
        func (Callable): The function to be wrapped with error handling.

    Returns:
        Callable: A wrapper function that includes error handling.

    Raises:
        AuthenticationError: If authentication fails.
        BadRequestError: If the request is invalid.
        PermissionDeniedError: If permission is denied.
        NotFoundError: If the resource is not found.
        RateLimitError: If the rate limit is exceeded.
        APIConnectionError: For API connection issues, including timeout errors.
        InternalServerError: If there's an internal server error.
        APIError: For unexpected API errors.
        AnthropicError: For unexpected Anthropic-specific errors.
        Exception: For any other unexpected errors.
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError) as e:
            # Retryable errors
            retry_after = getattr(e.response.headers, "retry-after", 30) if hasattr(e, "response") else None
            logger.warning(f"Retryable error in {func.__name__}: {str(e)}")
            raise RetryableLLMError(str(e), e, retry_after=retry_after) from e
        except (AuthenticationError, BadRequestError, PermissionDeniedError, AnthropicError) as e:
            # Non-retryable errors
            logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
            raise NonRetryableLLMError(str(e), e) from e

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError) as e:
            # Retryable errors
            retry_after = getattr(e.response.headers, "retry-after", 30) if hasattr(e, "response") else None
            logger.warning(f"Retryable error in {func.__name__}: {str(e)}")
            raise RetryableLLMError(str(e), e, retry_after=retry_after) from e
        except (AuthenticationError, BadRequestError, PermissionDeniedError, AnthropicError) as e:
            # Non-retryable errors
            logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
            raise NonRetryableLLMError(str(e), e) from e

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def supabase_operation(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to handle Supabase database operation errors.

    Catches exceptions during Supabase operations, logs the error,
    and raises a custom DatabaseError.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.

    Raises:
        DatabaseError: If any exception occurs during the Supabase operation.
    """

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed in {func.__name__}: {e}", exc_info=True)
            raise DatabaseError(message=str(e), operation=func.__name__, entity_type="Supabase", cause=e) from e

    return async_wrapper
