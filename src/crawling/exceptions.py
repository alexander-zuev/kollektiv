from src.crawling.models import CrawlJob


class CrawlerException(Exception):
    """Base exception class for the crawler module."""
    pass

class JobException(Exception):
    """Base for job-related errors"""
    def __init__(self, job_id: str, message: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id}: {message}")

class JobNotFoundException(JobException):
    def __init__(self, job_id: str):
        super().__init__(job_id, "not found")

class JobNotCompletedError(JobException):
    def __init__(self, job_id: str):
        super().__init__(job_id, "job not completed yet")

class FireCrawlAPIException(CrawlerException):
    pass

class FireCrawlAPIConnectionError(CrawlerException):
    pass

class FireCrawlAPITimeoutException(FireCrawlAPIException):
    pass

class WebhookException(CrawlerException):
    """Base for webhook-related errors"""
    pass

class InvalidWebhookEventError(WebhookException):
    """Raised when webhook event is invalid"""
    pass