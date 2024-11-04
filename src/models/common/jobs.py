# TODO: Transition to redis for job management. There is no reason to use custom implementation.
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class CrawlJobStatus(str, Enum):
    """

    Represents the status of a web crawling job.

    Attributes:
        COMPLETED (str): Indicates that the crawl job has completed successfully.
        FAILED (str): Indicates that the crawl job has failed.
        IN_PROGRESS (str): Indicates that the crawl job is currently in progress.
        PENDING (str): Indicates that the crawl job is pending and has not yet been started.
        CANCELLED (str): Indicates the job was cancelled by the user.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlJob(BaseModel):
    """Track crawl job status and progress"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    firecrawl_id: str
    status: CrawlJobStatus
    start_url: str
    method: str = Field(default="crawl")

    # Simple progress tracking
    pages_crawled: int = 0

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    result_file: str | None = None
    error: str | None = None

    class Config:
        """Configuration class for CrawlJob model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
