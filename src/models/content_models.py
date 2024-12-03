from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

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


class FireCrawlMetadata(BaseModel):
    """General metadata about Firecrawl data sources."""

    # Created initially
    start_url: str = Field(..., alias="url", description="The original start URL of the crawl")
    page_limit: int = Field(default=50, gt=0, description="Maximum number of pages to crawl.")
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="The list of patterns to exclude, e.g., '/blog/*', '/author/*'.",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="The list of patterns to include, e.g., '/blog/*', '/api/*'.",
    )

    # Added after crawl is finished
    total_pages: int = Field(default=0, ge=0, description="Total number of pages successfully crawled")
    unique_links: list[str] = Field(default_factory=list, description="List of unique URLs discovered during crawling")
    error_message: str | None = Field(None, description="Error message if the crawl failed")

    class Config:
        """Allows using both alias and non-alias names."""

        populate_by_name = True  # Allows both 'url' and 'start_url' to be used


class DataSource(BaseDbModel):
    """Base model for all raw data sources loaded into the system."""

    _db_config: ClassVar[dict] = {"schema": "content", "table": "data_sources", "primary_key": "source_id"}

    # User-related
    # user_id: UUID = Field(..., description="User id, FK, provided by Supabase base after auth.")

    source_id: UUID = Field(default_factory=uuid4)
    source_type: DataSourceType = Field(
        ..., description="Type of the data source corresponding to supported data source types"
    )
    status: SourceStatus = Field(..., description="Status of the content source in the system.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Source-specific configuration and metadata. Schema depends on source_type"
    )
    request_id: UUID = Field(..., description="Request id of the user request to add content")
    job_id: UUID | None = Field(default=None, description="UUID of the job in the system.")

    error: str | None = Field(default=None, description="Error message, null if no error")

    # Define protected fields that cannot be updated
    _protected_fields: set[str] = PrivateAttr(default={"source_id", "source_type", "created_at"})


# Document models
class Document(BaseDbModel):
    """Represents a single piece of content (i.e. a page) from a source."""

    document_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the document")
    source_id: UUID = Field(
        ...,  # Can't be required but should be here somehow
        description="ID of the source this document belongs to",
    )
    content: str = Field(
        ...,  # Required
        description="Raw content of the document in markdown format",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Flexible metadata storage for document-specific information"
    )
    _db_config: ClassVar[dict] = {"schema": "content", "table": "documents", "primary_key": "document_id"}

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class DocumentMetadata(BaseModel):
    """
    Flexible metadata container for document-specific information.

    Accepts any number of keyword arguments which become metadata fields.
    Common fields might include:
    - description: Document description or summary
    - keywords: List of keywords or tags
    - author: Document author
    - last_modified: Last modification timestamp
    - language: Document language
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize metadata with arbitrary keyword arguments."""
        super().__init__(**kwargs)


class Chunk(BaseModel):
    """Individual chunk of content with metadata"""

    # References
    chunk_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the chunk")
    document_id: UUID = Field(..., description="UUID of the document this chunk belongs to")
    source_id: UUID = Field(..., description="UUID of the source this chunk belongs to")

    # Main content
    headers: dict[str, Any] = Field(..., description="Chunk headers")
    text: str = Field(..., description="Chunk text")

    # Metadata
    token_count: int = Field(..., description="Total number of tokens in the document")
    source_url: str = Field(..., description="Source URL of the document")
    page_title: str = Field(..., description="Page title of the document")


class DocumentChunk(BaseDbModel):
    """Represents a chunk of content from a document."""

    _db_config: ClassVar[dict] = {"schema": "content", "table": "document_chunks", "primary_key": "document_id"}

    document_id: UUID = Field(..., description="FK UUID of the document this chunk belongs to")
    source_id: UUID = Field(..., description="FK UUID of the source this chunk belongs to")
    chunks: list[Chunk] = Field(..., description="JSONB array of chunks")
    metadata: dict[str, Any] = Field(
        ...,
        description="Metadata about the document chunking process",
    )


class DocumentChunkMetadata(BaseModel):
    """Metadata about the document chunking process"""

    chunk_ids: list[UUID] = Field(..., description="List of chunk IDs related to the document")
    chunk_count: int = Field(..., description="Number of chunks")
    total_tokens: int = Field(..., description="Total number of tokens in the document")
    avg_chunk_size: int = Field(..., description="Average size of the chunks")
