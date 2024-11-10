from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    """Enum of all different data sources supported by Kollektiv."""

    WEB = "web"
    GITHUB = "github"
    JIRA = "jira"
    CONFLUENCE = "confluence"


class SourceStatus(str, Enum):
    """Model of Source Status."""

    PENDING = "pending"  # right after creation
    CRAWLING = "crawling"  # after crawling started
    PROCESSING = "processing"  # during chunking and embedding
    COMPLETED = "completed"  # after loading is complete
    FAILED = "failed"  # if addition failed


class Source(BaseModel):
    """Base model for all raw data sources loaded into the system."""

    source_id: UUID = Field(default_factory=uuid4)
    source_type: DataSourceType = Field(
        ..., description="Type of the data source corresponding to supported data source types"
    )
    data: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    status: SourceStatus = Field(..., description="Status of the content source in the system.")
    job_id: str | None = Field(None, description="Job id in the system.")
