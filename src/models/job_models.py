# TODO: Transition to redis for job management. There is no reason to use custom implementation.
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

from src.models.base_models import SupabaseModel


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Represents the type of a job."""

    CRAWL = "crawl"
    PROCESSING = "processing"


class CrawlJobDetails(BaseModel):
    """Detailed information about a crawl job."""

    source_id: UUID = Field(
        ...,
        description="Maps each crawl job to the Source object.",
    )
    firecrawl_id: str | None = Field(
        default=None, description="Job id returned by FireCrawl. Added only if a jobs starts successfully"
    )
    pages_crawled: int = Field(default=0, description="Number of pages crawled")
    url: str = Field(..., description="URL that was crawled")


class ProcessingJobDetails(BaseModel):
    """Detailed information about a processing job - chunking and vector storage."""

    source_id: UUID = Field(..., description="Maps each processing job to the Source object.")
    document_ids: list[UUID] = Field(..., description="List of document ids to be processed.")


class Job(SupabaseModel):
    """Track crawl job status and progress"""

    # General job info
    job_id: UUID = Field(default_factory=uuid4, description="Internal job id in the system")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Crawl job status in the system.")
    job_type: JobType = Field(..., description="Type of the job.")

    # Job details
    details: CrawlJobDetails | ProcessingJobDetails = Field(..., description="Detailed information about the job.")

    # Timing
    completed_at: datetime | None = Field(None, description="Completion timestamp")

    # Results
    error: str | None = None

    _db_config: ClassVar[dict] = {"schema": "infra", "table": "jobs", "primary_key": "job_id"}
    _protected_fields: set[str] = PrivateAttr(default={"job_id", "job_type", "created_at"})

    def update(self, **kwargs: Any) -> Job:
        """Update job fields while preserving protected fields."""
        if "details" in kwargs and isinstance(kwargs["details"], dict):
            # Get current details as dict
            current_details = self.details.model_dump()
            # Update with new values
            current_details.update(kwargs["details"])
            # Replace details update with merged version
            kwargs["details"] = current_details

        return super().update(**kwargs)

    def complete(self) -> None:
        """Mark job as completed."""
        if self.status == JobStatus.COMPLETED:
            return
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        if self.status == JobStatus.FAILED:
            return
        self.status = JobStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(UTC)

    class Config:
        """Configuration class for CrawlJob model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
