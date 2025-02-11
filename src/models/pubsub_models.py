from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """High-level categorization of events in the system."""

    CONTENT_PROCESSING = "content_processing"
    # Later we might add:
    # AUTH = "auth"
    # BILLING = "billing"
    # etc.


class KollektivEvent(BaseModel):
    """Base model for all events emitted by the Kollektiv tasks."""

    event_type: EventType = Field(..., description="Type of the event")
    error: str | None = Field(default=None, description="Error message, null if no error")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for the event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp of the event")


class ContentProcessingStage(str, Enum):
    """Enum of all different content processing stages."""

    STARTED = "started"  # When processing started
    CHUNKS_GENERATED = "chunks_generated"  # When chunks are generated
    SUMMARY_GENERATED = "summary_generated"  # When summary is generated
    COMPLETED = "completed"  # When processing complete
    FAILED = "failed"  # When processing fails


class ContentProcessingEvent(KollektivEvent):
    """Events related to content ingestion."""

    event_type: EventType = Field(..., description="Type of the event")
    source_id: UUID = Field(..., description="ID of the source this event belongs to")
    stage: ContentProcessingStage = Field(..., description="Status of the event")
