from src.crawling.models import CrawlJob


class CrawlerException(Exception):
    """Base exception class for the crawler module."""

    pass


class JobException(CrawlerException):
    """Base for job-related errors"""

    def __init__(self, job_id: str, message: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id}: {message}")


class JobNotFoundException(JobException):
    """Exception raised when a job cannot be found."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "not found")


class JobNotCompletedError(JobException):
    """Exception raised when attempting to access results of an incomplete job."""

    def __init__(self, job_id: str):
        super().__init__(job_id, "job not completed yet")


class EmptyContentError(CrawlerException):
    """Raised when crawled content is empty"""

    def __init__(self, url: str):
        super().__init__(f"Empty content received from {url}")


class FireCrawlAPIError(CrawlerException):
    """Base for FireCrawl API errors"""

    pass


class FireCrawlConnectionError(FireCrawlAPIError):
    """Connection issues with FireCrawl API"""

    pass


class FireCrawlTimeoutError(FireCrawlAPIError):
    """Timeout from FireCrawl API"""

    pass


class WebhookException(CrawlerException):
    """Base for webhook-related errors"""

    pass


class InvalidWebhookEventError(WebhookException):
    """Invalid webhook event received"""

    pass
