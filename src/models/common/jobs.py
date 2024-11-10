# TODO: Transition to redis for job management. There is no reason to use custom implementation.
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

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

    job_id: UUID = Field(default_factory=lambda: uuid4(), description="Internal job id in the system")
    source_id: UUID = Field(..., description="Maps each crawl job to the Source object.")
    firecrawl_id: str | None = Field(
        None, description="Job id returned by FireCrawl. Added only if a jobs starts " "successfully"
    )
    status: CrawlJobStatus = Field(default=CrawlJobStatus.PENDING, description="Crawl job status in the system.")
    method: str = Field(default="crawl")

    # Simple progress tracking
    pages_crawled: int = 0

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # Results
    result_file: str | None = None
    error: str | None = None

    class Config:
        """Configuration class for CrawlJob model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
