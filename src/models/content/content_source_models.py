from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr


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


class DataSource(BaseModel):
    """Base model for all raw data sources loaded into the system."""

    source_id: UUID = Field(default_factory=uuid4)
    source_type: DataSourceType = Field(
        ..., description="Type of the data source corresponding to supported data source types"
    )
    status: SourceStatus = Field(..., description="Status of the content source in the system.")
    metadata: dict[str, Any] = Field(
        ..., description="Source-specific configuration and metadata. Schema depends on source_type"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp of creation by the application."
    )
    updated_at: datetime | None = None
    request_id: UUID = Field(..., description="Request id of the user request to add content")
    job_id: UUID | None = Field(None, description="UUID of the job in the system.")

    # Define protected fields that cannot be updated
    _protected_fields: set[str] = PrivateAttr(default={"source_id", "source_type", "created_at"})

    def update(self, **kwargs: Any) -> DataSource:
        """
        Update data source fields while preserving protected fields.

        Args:
            **kwargs: Fields to update and their new values

        Returns:
            DataSource: Updated data source instance

        Example:
            data_source.update(status=SourceStatus.COMPLETED, completed_at=datetime.now(UTC))
        """
        # Filter out protected fields
        allowed_updates = {k: v for k, v in kwargs.items() if k not in self._protected_fields}

        # Metadata is a dict, no need for special handling
        # Just let Pydantic handle validation through model_copy

        # Update the model
        return self.model_copy(update=allowed_updates)
