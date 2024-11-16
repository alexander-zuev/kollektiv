from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field, PrivateAttr

from src.models.base_models import BaseDbModel


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


class DataSource(BaseDbModel):
    """Base model for all raw data sources loaded into the system."""

    _db_config: ClassVar[dict] = {"schema": "content", "table": "data_sources", "primary_key": "source_id"}

    source_id: UUID = Field(default_factory=uuid4)
    source_type: DataSourceType = Field(
        ..., description="Type of the data source corresponding to supported data source types"
    )
    status: SourceStatus = Field(..., description="Status of the content source in the system.")
    metadata: dict[str, Any] = Field(
        ..., description="Source-specific configuration and metadata. Schema depends on source_type"
    )
    request_id: UUID = Field(..., description="Request id of the user request to add content")
    job_id: UUID | None = Field(None, description="UUID of the job in the system.")

    # Define protected fields that cannot be updated
    _protected_fields: set[str] = PrivateAttr(default={"source_id", "source_type", "created_at"})
