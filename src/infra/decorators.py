import asyncio
import functools
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import tenacity
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
        except Exception:
            raise

    return wrapper


def generic_error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """Simple error handler that preserves the original error context."""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception:
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception:
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


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
            logger.exception(f"Database error in {func.__name__}: {e.error_message}")
            raise e from None
        except EntityNotFoundError as e:
            logger.warning(f"Entity not found error in {func.__name__}: {e.error_message}")
            raise e from None
        except EntityValidationError as e:
            logger.exception(f"Entity validation error in {func.__name__}: {e.error_message}")
            raise e from None
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise DatabaseError(
                error_message=f"Unexpected error in {func.__name__}",
                operation=func.__name__,
                entity_type=None,
                details={"error": str(e)},
                cause=e,
            ) from e

    return async_wrapper


def tenacity_retry_wrapper(
    exceptions: tuple[type[Exception], ...] | None = None,
    multiplier: int = 2,
    min_wait: int = 2,
    max_wait: int = 30,
    max_attempts: int = 3,
) -> Callable[..., RT]:
    """Create a retry decorator with configurable exceptions.

    Args:
        exceptions: Tuple of exceptions to catch. Defaults to (Exception,) if None
        multiplier: Multiplier for the exponential backoff
        min_wait: Minimum wait time between attempts
        max_wait: Maximum wait time between attempts
        max_attempts: Maximum number of attempts

    Retries:
        - Wait 2-30 seconds between attempts
        - Up to a total of 60 seconds
    """
    # Get logger from the calling module
    logger = get_logger()

    return tenacity.retry(
        retry=tenacity.retry_if_exception_type(exceptions or (Exception,)),
        wait=tenacity.wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        stop=tenacity.stop_after_attempt(max_attempts),
        before_sleep=lambda retry_state: logger.warning(f"Attempt {retry_state.attempt_number} failed. Retrying..."),
    )
