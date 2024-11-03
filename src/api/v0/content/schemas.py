from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ContentSourceType(str, Enum):
    """Supported content source types."""

    WEB = "web"  # Web crawling
    # Future: CONFLUENCE = "confluence"  # Future: Confluence integration
    # Future: JIRA = "jira"  # Future: Jira integration
    # Future: GITHUB = "github"  # Future: GitHub docs/wikis


class AddContentSourceRequest(BaseModel):
    """Request to add new content source."""

    type: ContentSourceType = Field(..., description="Type of content source")
    name: str = Field(..., description="Display name for content source")
    url: HttpUrl = Field(..., description="Base URL of the content")

    # Source-specific configuration
    config: dict = Field(default_factory=dict, description="Source-specific configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "web",
                "name": "Product Docs",
                "url": "https://docs.example.com",
                "config": {"max_pages": 50, "exclude_paths": ["/blog/*"], "crawl_frequency": "daily"},
            }
        }


class ContentSourceStatus(str, Enum):
    """Content source processing status."""

    PENDING = "pending"  # Source created
    PROCESSING = "processing"  # Crawling / processing
    COMPLETED = "completed"  # Source added
    FAILED = "failed"  # Error occured


class ContentSourceResponse(BaseModel):
    """Content source details."""

    id: str
    type: ContentSourceType
    name: str
    url: str
    status: ContentSourceStatus
    document_count: int
    last_sync: datetime | None
    config: dict
