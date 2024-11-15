from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """
    Represents the status of a job in the system.

    Attributes:
        COMPLETED (str): Indicates that a job has completed successfully.
        FAILED (str): Indicates that a job has failed.
        IN_PROGRESS (str): Indicates that a job is currently in progress.
        PENDING (str): Indicates that a job is pending and has not yet been started.
        CANCELLED (str): Indicates a job was cancelled by the user.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """
    The type of job in the system.

    Attributes:
        FIRECRAWL (str): Firecrawl-related jobs.
    """

    FIRECRAWL = "firecrawl"
    # other types might be added later


class CrawlJobDetails(BaseModel):
    """Details specific to crawl jobs."""

    source_id: UUID = Field(..., description="Reference to the data source object by UUID.")
    firecrawl_id: str | None = Field(
        None, description="Job id returned by FireCrawl. Added only if a job starts successfully."
    )
    pages_crawled: int = Field(default=0, description="Number of pages crawled so far.")


class Job(BaseModel):
    """Generic job model for tracking job status and progress."""

    # General details
    job_id: UUID = Field(default_factory=lambda: uuid4(), description="Internal job id in the system")
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Job status in the system. Defaults to PENDING when created.",
    )
    job_type: JobType = Field(..., description="Type of the job.")

    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp of when the job was created."
    )
    completed_at: datetime | None = Field(
        None, description="UTC timestamp of job completion. Null if job failed or not completed."
    )

    # Results
    result_id: UUID | None = Field(None, description="Reference to id of the result object.")
    error: str | None = Field(None, description="Error message if job failed.")

    # Job-specific details stored as JSON
    details: dict[str, Any] | None = Field(None, description="Job type specific details stored as JSON.")

    class Config:
        """Configuration class for Job model."""

        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions for creating specific job types
def create_crawl_job(source_id: UUID) -> Job:
    """Create a new crawl job with appropriate details."""
    details = CrawlJobDetails(source_id=source_id)

    return Job(job_type=JobType.FIRECRAWL, details=details.model_dump())


# Helper functions for accessing job details
def get_crawl_details(job: Job) -> CrawlJobDetails | None:
    """Extract crawl job details from a job if it's a crawl job."""
    if job.job_type == JobType.FIRECRAWL and job.details:
        return CrawlJobDetails.model_validate(job.details)
    return None
