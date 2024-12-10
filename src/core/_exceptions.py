from typing import Self
from uuid import UUID

from requests.exceptions import HTTPError, Timeout


class KollektivError(Exception):
    """Base class for Kollektiv exceptions."""

    def __init__(self, error_message: str | None):
        """Create an exception with an optional error error_message"""
        self.error_message = error_message

    pass


class RetryableError(KollektivError):
    """Base class for retryable errors."""

    def __init__(self, error_message: str, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(error_message)


class NonRetryableError(KollektivError):
    """Base class for non-retryable errors."""

    pass


# General errors
## User-input
class ValidationError(NonRetryableError):
    """Raised when input validation fails."""

    pass


## App configuration


# API errors
class WebhookError(KollektivError):
    """Base for webhook-related errors."""

    pass


class InvalidWebhookEventError(WebhookError):
    """Invalid webhook event received."""

    pass


# Chat-related errors
# Content-related errors
class DataSourceError(KollektivError):
    """Exception raised for errors related to Data Source operations."""

    def __init__(self, source_id: UUID, error_message: str, original_exception: Exception | None = None):
        self.source_id = source_id
        self.error_message = error_message
        self.original_exception = original_exception
        super().__init__(f"DataSourceError for source_id={source_id}: {error_message}")


## Firecrawl errors
class RateLimitError(RetryableError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        super().__init__("Rate limit exceeded", retry_after)


class TemporaryError(RetryableError):
    """Temporary server error."""

    pass


def is_retryable_error(exception: Exception) -> tuple[bool, int | None]:
    """
    Determine if an error should trigger a retry attempt.

    Returns:
        tuple[bool, int | None]: (should_retry, retry_after_seconds)
    """
    if isinstance(exception, HTTPError):
        status_code = exception.response.status_code
        retry_after = exception.response.headers.get("Retry-After")

        if status_code == 429:  # Rate limit
            return True, int(retry_after) if retry_after else 30
        if status_code in [500, 502, 503, 504]:  # Server errors
            return True, None

    if isinstance(exception, FireCrawlConnectionError | Timeout):
        return True, None

    return False, None


class CrawlerError(KollektivError):
    """Base exception class for the crawler module."""

    pass


class FireCrawlAPIError(CrawlerError, NonRetryableError):
    """Base for FireCrawl API errors."""

    pass


class FireCrawlJobNotFound(CrawlerError, NonRetryableError):
    """Job with given firecrawl ids not found"""

    pass


class FireCrawlConnectionError(CrawlerError, RetryableError):
    """Connection issues with FireCrawl API."""

    pass


class FireCrawlTimeoutError(CrawlerError, RetryableError):
    """Timeout from FireCrawl API."""

    pass


class EmptyContentError(CrawlerError, RetryableError):
    """Raised when crawled content is empty."""

    def __init__(self, url: str):
        super().__init__(f"Empty content parsed from  {url}. Please ensure crawler settings are correct and try again.")


# Search-related errors
# Infrastructure-related errors
## Supabase


class DatabaseError(NonRetryableError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        error_message: str,
        operation: str,
        entity_type: str,
        details: dict | None = None,
        cause: Exception | None = None,
    ):
        self.operation = operation
        self.entity_type = entity_type
        self.details = details or {}
        self.cause = cause
        super().__init__(error_message)

    def add_context(self, operation: str, entity_type: str) -> Self:
        """Adds context information to the exception."""
        self.operation = operation or self.operation  # Don't overwrite if already set
        self.entity_type = entity_type or self.entity_type  # Don't overwrite if already set
        return self


class EntityNotFoundError(DatabaseError):
    """Raised when an entity is not found in the database."""

    def __init__(self, error_message: str, operation: str, entity_type: str):
        self.error_message = error_message
        super().__init__(error_message, operation=operation, entity_type=entity_type)


class EntityValidationError(DatabaseError):
    """Raised when entity validation fails."""

    def __init__(self, entity_type: str, validation_errors: dict, operation: str):
        self.entity_type = entity_type
        self.validation_errors = validation_errors
        error_message = f"Validation failed for {entity_type}: {validation_errors}"
        super().__init__(error_message, entity_type=entity_type, operation=operation)


class BulkOperationError(DatabaseError):
    """Raised when a bulk database operation fails."""

    def __init__(self, entity_type: str, operation: str, failed_items: list, error: Exception | None = None):
        self.operation = operation
        self.failed_items = failed_items
        self.original_error = error
        error_message = f"Bulk {operation} failed for {len(failed_items)} items"
        super().__init__(error_message, entity_type=entity_type, operation=operation)


## Vector storage
## Job management
class JobError(NonRetryableError):
    """An application-level job errors. Internal to the kollektiv backend application."""

    def __init__(self, job_id: str, error_message: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id}: {error_message}")


class JobNotFoundError(JobError):
    """Exception raised when a job cannot be found."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "not found")


class JobNotCompletedError(JobError):
    """Exception raised when attempting to access results of an incomplete job."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "job not completed yet")


class JobUpdateError(JobError):
    """Exception raised when a job update fails."""

    def __init__(self, job_id: str, reason: str):
        super().__init__(job_id, f"update failed: {reason}")


class JobValidationError(JobError):
    """Exception raised when job data is invalid."""

    def __init__(self, job_id: str, reason: str):
        super().__init__(job_id, f"validation failed: {reason}")


class JobStateError(JobError):
    """Exception raised when job state transition is invalid."""

    def __init__(self, job_id: str, current_state: str, attempted_state: str):
        super().__init__(job_id, f"invalid state transition from {current_state} to {attempted_state}")


## Queue and workers


class LLMError(KollektivError):
    """Base class for LLM-related errors."""

    pass


class StreamingError(LLMError):
    """Raised when streaming operations fail."""

    pass


class TokenLimitError(StreamingError):
    """Raised when token limit is exceeded during streaming."""

    pass


class ConnectionError(StreamingError):
    """Raised when streaming connection is interrupted."""

    pass


class ClientDisconnectError(StreamingError):
    """Raised when client disconnects during streaming."""

    pass


class RetryableLLMError(RetryableError, LLMError):
    """Base class for retryable LLM errors."""

    def __init__(self, message: str, original_error: Exception, retry_after: int | None = None):
        super().__init__(f"Temporary error in chat: {message}. Please try again.", retry_after)
        self.original_error = original_error


class NonRetryableLLMError(NonRetryableError, LLMError):
    """Base class for non-retryable LLM errors."""

    def __init__(self, message: str, original_error: Exception):
        super().__init__(f"A non-retryable error occured in Anthropic chat: {message}")
        self.original_error = original_error
