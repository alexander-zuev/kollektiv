from requests.exceptions import HTTPError, Timeout


class CrawlerError(Exception):
    """Base exception class for the crawler module."""

    pass


class JobError(CrawlerError):
    """Base for job-related errors."""

    def __init__(self, job_id: str, message: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id}: {message}")


class JobNotFoundError(JobError):
    """Exception raised when a job cannot be found."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "not found")


class JobNotCompletedError(JobError):
    """Exception raised when attempting to access results of an incomplete job."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "job not completed yet")


class EmptyContentError(CrawlerError):
    """Raised when crawled content is empty."""

    def __init__(self, url: str):
        super().__init__(f"Empty content received from {url}")


class FireCrawlAPIError(CrawlerError):
    """Base for FireCrawl API errors."""

    pass


class FireCrawlConnectionError(FireCrawlAPIError):
    """Connection issues with FireCrawl API."""

    pass


class FireCrawlTimeoutError(FireCrawlAPIError):
    """Timeout from FireCrawl API."""

    pass


class WebhookError(CrawlerError):
    """Base for webhook-related errors."""

    pass


class InvalidWebhookEventError(WebhookError):
    """Invalid webhook event received."""

    pass


class RetryableError(CrawlerError):
    """Base class for errors that can be retried."""

    def __init__(self, message: str, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(message)


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
