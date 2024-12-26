import asyncio
import functools
import sys
from collections.abc import Callable, Coroutine
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

from src.core._exceptions import (
    DatabaseError,
    EntityNotFoundError,
    EntityValidationError,
    NonRetryableLLMError,
    RetryableLLMError,
)
from src.infra.logger import get_logger

logger = get_logger()

RT = TypeVar("RT")
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
    Applies error handling for various exceptions encountered during Anthropic API calls.

    This decorator catches and handles specific exceptions from the Anthropic API,
    raising custom exceptions for retryable and non-retryable errors.

    Args:
        func (Callable): The function to be wrapped with error handling.

    Returns:
        Callable: A wrapper function that includes error handling.

    Raises:
        RetryableLLMError: For errors that can be retried, such as rate limits or timeouts.
        NonRetryableLLMError: For errors that cannot be retried, such as authentication or bad requests.
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


def supabase_operation(func: Callable[P, Coroutine[Any, Any, RT]]) -> Callable[P, Coroutine[Any, Any, RT]]:
    """
    Handles common Supabase operations and errors.

    This decorator catches common exceptions that can occur during Supabase
    operations, such as database errors, entity not found errors, and
    validation errors. It also handles logging of these errors.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.

    Raises:
        DatabaseError: If a database error occurs.
        EntityNotFoundError: If an entity is not found.
        EntityValidationError: If an entity fails validation.
    """

    @wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
        try:
            return await func(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e.error_message}")
            raise e from None
        except EntityNotFoundError as e:
            logger.warning(f"Entity not found error in {func.__name__}: {e.error_message}")
            raise e from None
        except EntityValidationError as e:
            logger.error(f"Entity validation error in {func.__name__}: {e.error_message}")
            raise e from None
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise DatabaseError(
                error_message=f"Unexpected error in {func.__name__}",
                operation=func.__name__,
                entity_type=None,
                details={"error": str(e)},
                cause=e,
            ) from e

    return async_wrapper
