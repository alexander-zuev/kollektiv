# TODO: Transition to redis for job management. There is no reason to use custom implementation.
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

from src.models.base_models import BaseDbModel


class JobStatus(str, Enum):
    """

    Represents the status of a web crawling job.

    Attributes:
        PENDING: Indicates that the crawl job is pending and has not yet been started.
        IN_PROGRESS: Indicates that the crawl job is currently in progress.
        COMPLETED: Indicates that the crawl job has completed successfully.
        FAILED: Indicates that the crawl job has failed.
        CANCELLED: Indicates the job was cancelled by the user.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Represents the type of a job."""

    CRAWL = "crawl"


class CrawlJobDetails(BaseModel):
    """Detailed information about a crawl job."""

    source_id: UUID = Field(
        ...,
        description="Maps each crawl job to the Source object.",
    )
    firecrawl_id: str | None = Field(
        None, description="Job id returned by FireCrawl. Added only if a jobs starts successfully"
    )
    pages_crawled: int = Field(default=0, description="Number of pages crawled")
    url: str = Field(..., description="URL that was crawled")


class Job(BaseDbModel):
    """Track crawl job status and progress"""

    _db_config: ClassVar[dict] = {"schema": "infra", "table": "jobs", "primary_key": "job_id"}
    _protected_fields: set[str] = PrivateAttr(default={"job_id", "job_type", "created_at"})

    # General job info
    job_id: UUID = Field(default_factory=uuid4, description="Internal job id in the system")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Crawl job status in the system.")
    job_type: JobType = Field(..., description="Type of the job.")

    # Job details
    details: dict = Field(..., description="Detailed information about the job.")

    # Timing
    completed_at: datetime | None = Field(None, description="Completion timestamp")

    # Results
    result_id: UUID | None = Field(default=None, description="ID of the result file in the storage")
    error: str | None = None

    def update(self, **kwargs: Any) -> Job:
        """
        Update job fields while preserving protected fields.

        Args:
            **kwargs: Fields to update and their new values

        Returns:
            Job: Updated job instance

        Example:
            job.update(status=CrawlJobStatus.COMPLETED, completed_at=datetime.now(UTC))
        """
        # If updating details and it's a CRAWL job, validate details
        if "details" in kwargs and self.job_type == JobType.CRAWL:
            current_details = CrawlJobDetails.model_validate(self.details)
            new_details = current_details.model_copy(update=kwargs["details"])
            kwargs["details"] = new_details.model_dump()

        # Use parent's update method for the rest
        return super().update(**kwargs)

    class Config:
        """Configuration class for CrawlJob model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
