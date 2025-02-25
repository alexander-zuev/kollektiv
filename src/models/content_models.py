from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, PrivateAttr, ValidationError, field_validator

from src.infra.logger import get_logger
from src.models.base_models import APIModel, SupabaseModel
from src.models.pubsub_models import EventType, KollektivEvent

logger = get_logger()


class DataSourceType(str, Enum):
    """Enum of all different data sources supported by Kollektiv."""

    WEB = "web"
    GITHUB = "github"
    JIRA = "jira"
    CONFLUENCE = "confluence"


class ContentSourceConfig(APIModel):
    """Configuration parameters for a content source."""

    url: str = Field(..., description="Start URL of the crawl.")
    page_limit: int = Field(default=50, gt=0, description="Maximum number of pages to crawl.")
    exclude_paths: list[str] = Field(
        default_factory=list,
        description="The list of patterns to exclude, e.g., '/blog/*', '/author/*'.",
    )
    include_paths: list[str] = Field(
        default_factory=list,
        description="The list of patterns to include, e.g., '/blog/*', '/api/*'.",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validates start url of the crawl and returns a str."""
        try:
            parsed = HttpUrl(str(v))
            return str(parsed)  # Convert to string immediately
        except Exception as e:
            raise ValueError("Invalid URL. It should start with 'http://' or 'https://'.") from e

    @field_validator("exclude_paths", "include_paths")
    def validate_paths(cls, v: list[str]) -> list[str]:  # noqa: N805
        """

        Validates patterns to ensure they start with '/' and are not empty.

        Args:
            cls: The class instance.
            v (list[str]): List of string patterns to validate.

        Returns:
            list[str]: The validated list of patterns.

        Raises:
            ValueError: If any pattern is empty or does not start with '/'.
        """
        for pattern in v:
            if not pattern.strip():
                raise ValueError("Empty patterns are not allowed")
            if not pattern.startswith("/"):
                raise ValueError("Pattern must start with '/', got: {pattern}")
        return v


class AddContentSourceRequest(SupabaseModel, APIModel):
    """
    Request model for adding a new content source.

    Attributes:
        request_id: System-generated UUID for tracking the request. Auto-generated if not provided.
        source_type: Type of content source (currently only 'web' is supported).
        request_config: Configuration parameters for the content source.

    Example:
        ```json
        {
            "request_config": {
                "url": "https://docs.example.com",
                "page_limit": 50,
                "exclude_patterns": ["/blog/*"],
                "include_patterns": ["/api/*"]
            },
            "source_type": "web"  # Optional, defaults to "web"
        }
        ```
    """

    _db_config: ClassVar[dict] = {"schema": "content", "table": "user_requests", "primary_key": "request_id"}
    user_id: UUID = Field(..., description="User id, FK, provided by Supabase base after auth.")
    request_id: UUID = Field(default_factory=uuid4, description="System-generated id of a user request.")
    source_type: DataSourceType = Field(
        default=DataSourceType.WEB,  # Make web the default
        description="Type of content source (currently only 'web' is supported).",
    )
    request_config: ContentSourceConfig = Field(
        ...,  # Required
        description="Configuration parameters for the content source",
    )

    class Config:
        """Example configuration."""

        json_schema_extra = {
            "example": {
                "request_config": {
                    "url": "https://docs.example.com",
                    "page_limit": 50,
                    "exclude_patterns": ["/blog/*"],
                    "include_patterns": ["/api/*"],
                },
                "source_type": "web",
            }
        }


class AddContentSourceRequestDB(SupabaseModel):
    """Model for adding a new content source in the database."""

    _db_config: ClassVar[dict] = {"schema": "content", "table": "user_requests", "primary_key": "request_id"}
    user_id: UUID = Field(..., description="User id, FK, provided by Supabase base after auth.")
    request_id: UUID = Field(default_factory=uuid4, description="System-generated id of a user request.")
    source_type: DataSourceType = Field(
        default=DataSourceType.WEB,  # Make web the default
        description="Type of content source (currently only 'web' is supported).",
    )
    request_config: ContentSourceConfig = Field(
        ...,  # Required
        description="Configuration parameters for the content source",
    )

    @classmethod
    def from_api_to_db(cls, request: AddContentSourceRequest) -> AddContentSourceRequestDB:
        """Convert an AddContentSourceRequest to an AddContentSourceRequestDB."""
        data = request.model_dump(by_alias=False)
        return cls(**data)


class AddContentSourceResponse(APIModel):
    """Simplified model inheriting from Source."""

    source_id: UUID = Field(...)
    stage: SourceStage = Field(..., description="Stage of the data source")
    # error: str | None = Field(None, description="Error message, null if no error")
    # error_type: Literal["crawler", "infrastructure"] | None = Field(None, description="Type of the error")

    @classmethod
    def from_source(cls, source: DataSource) -> AddContentSourceResponse:
        return cls(source_id=source.source_id, stage=source.stage, error=source.error, error_type=None)


class SourceStage(str, Enum):
    """Model of Source source stages throught the processing pipeline."""

    CREATED = "created"  # right after creation
    CRAWLING_STARTED = "crawling_started"  # after crawling started
    PROCESSING_SCHEDULED = "processing_scheduled"  # during chunking and embedding
    CHUNKS_GENERATED = "chunks_generated"  # after chunks generated
    SUMMARY_GENERATED = "generating_summary"  # during summary generation
    COMPLETED = "completed"  # after processing is complete
    FAILED = "failed"  # if addition failed


class DataSource(SupabaseModel):
    """Base model for all raw data sources loaded into the system."""

    _db_config: ClassVar[dict] = {"schema": "content", "table": "data_sources", "primary_key": "source_id"}

    source_id: UUID = Field(default_factory=uuid4, description="UUID of the source")
    user_id: UUID = Field(..., description="User id, FK, provided by Supabase base after auth.")
    request_id: UUID = Field(..., description="Request id of the user request to add content")
    job_id: UUID | None = Field(default=None, description="UUID of the job that is processing this source")

    source_type: DataSourceType = Field(
        ..., description="Type of the data source corresponding to supported data source types"
    )
    stage: SourceStage = Field(
        SourceStage.CREATED, description="Stage of the content source in the system, starts with created"
    )

    metadata: FireCrawlSourceMetadata = Field(
        ..., description="Source-specific configuration. Schema depends on source_type"
    )

    error: str | None = Field(default=None, description="Error message, null if no error")

    # Define protected fields that cannot be updated
    _protected_fields: set[str] = PrivateAttr(default={"source_id", "source_type", "created_at"})


class FireCrawlSourceMetadata(BaseModel):
    """Metadata for a FireCrawl source."""

    crawl_config: ContentSourceConfig = Field(..., description="Configuration of the crawl")
    total_pages: int = Field(default=0, description="Total number of pages in the source")


class SourceSummary(SupabaseModel):
    """A summary of a source document generated by an LLM."""

    summary_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the summary")
    source_id: UUID = Field(..., description="ID of the source this summary belongs to")
    summary: str = Field(..., description="Summary of the source document generated by the LLM")
    keywords: list[str] = Field(..., description="List of keywords or key topics generated by the LLM")

    _db_config: ClassVar[dict] = {"schema": "content", "table": "source_summaries", "primary_key": "summary_id"}

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


# Document models
class Document(SupabaseModel):
    """Represents a single piece of content (i.e. a page) from a source."""

    document_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the document")
    source_id: UUID = Field(
        ...,  # Can't be required but should be here somehow
        description="ID of the source this document belongs to",
    )
    content: str = Field(
        ...,  # Required
        description="Raw markdown content of the document",
    )
    metadata: DocumentMetadata = Field(..., description="Flexible metadata storage for document-specific information")

    _db_config: ClassVar[dict] = {"schema": "content", "table": "documents", "primary_key": "document_id"}


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    title: str = Field(default="Untitled", description="Title of the document")
    description: str = Field(default="No description", description="Description of the document")
    source_url: str = Field(default="", description="Source URL of the document")
    og_url: str = Field(default="", description="Open Graph URL of the document")


class Chunk(SupabaseModel):
    """Individual chunk of content with metadata"""

    # IDs
    chunk_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the chunk")
    source_id: UUID = Field(..., description="UUID of the source this chunk belongs to")
    document_id: UUID = Field(..., description="UUID of the document this chunk belongs to")

    # Main content
    headers: dict[str, Any] = Field(..., description="Chunk headers")
    text: str = Field(..., description="Chunk text")
    content: str | None = Field(
        default=None, description="Chunk content which is a combination of headers and text, used for embeddings"
    )

    # Metadata
    token_count: int = Field(..., description="Total number of tokens in the document")
    page_title: str = Field(..., description="Page title of the document")
    page_url: str = Field(..., description="Page URL of the document")

    # DB config
    _db_config: ClassVar[dict] = {"schema": "content", "table": "chunks", "primary_key": "chunk_id"}

    @field_validator("headers", mode="before")
    @classmethod
    def ensure_headers_is_dict(cls, value: Any) -> dict[str, Any]:
        """Ensure headers is a dict."""
        # If headers is provided as a JSON string, deserialize it.
        if isinstance(value, str):
            return json.loads(value)
        return value


class ContentProcessingEvent(KollektivEvent):
    """Events related to content ingestion."""

    source_id: UUID = Field(..., description="ID of the source this event belongs to")
    stage: SourceStage = Field(..., description="Status of the event")
    event_type: EventType = Field(EventType.CONTENT_PROCESSING, description="Type of the event")


# GET /sources/{source_id}/events
class SourceEvent(BaseModel):
    """SSE event model consumed by FE."""

    source_id: UUID = Field(..., description="ID of the source this event belongs to")
    stage: SourceStage = Field(..., description="Type of the event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp of the event")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for the event")
    error: str | None = Field(default=None, description="Error message, null if no error")

    @classmethod
    def from_processing_event(cls, event: ContentProcessingEvent) -> SourceEvent:
        """Deserializes a bytes ContentProcessingEvent into a SourceEvent."""
        try:
            return SourceEvent(
                source_id=event.source_id,
                stage=event.stage,
                metadata=event.metadata,
                error=event.error,
            )
        except ValidationError as e:
            logger.exception(
                f"Could not create SourceEvent from ContentProcessingEvent from stage {event.stage}: {str(e)}"
            )


# GET /sources
class SourceOverview(BaseModel):
    """An individual source with a summary and status. Displayed in the view sources form."""

    source_id: UUID = Field(..., description="ID of the source")
    is_active: bool = Field(..., description="Whether the source is active")
    summary: SourceSummary = Field(default=..., description="Summary of the source")


# PUT /sources/{source_id} <<< this can be a list
# DELETE /sources/{source_id} <<< this can be a list

# DELETE /sources/{source_id} <<< this can be a list
