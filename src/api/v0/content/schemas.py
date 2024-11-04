from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ContentSourceType(str, Enum):
    """Supported content source types."""

    WEB = "web"  # Web crawling
    # Future: CONFLUENCE = "confluence"  # Future: Confluence integration
    # Future: JIRA = "jira"  # Future: Jira integration
    # Future: GITHUB = "github"  # Future: GitHub docs/wikis


class ContentSourceConfig(BaseModel):
    """Standardized config for content sources."""

    max_pages: int = Field(default=50, gt=0)
    exclude_sections: list[str] = Field(default_factory=list)


class AddContentSourceRequest(BaseModel):
    """Request to add new content source."""

    type: ContentSourceType = Field(..., description="Type of content source")
    name: str = Field(..., description="Display name for content source")
    url: HttpUrl = Field(..., description="Base URL of the content")
    config: ContentSourceConfig  # Use typed config instead of dict

    class Config:
        json_schema_extra = {
            "example": {
                "type": "web",
                "name": "Product Docs",
                "url": "https://docs.example.com",
                "config": {
                    "max_pages": 50,
                    "exclude_paths": ["/blog/*"],
                },
            }
        }

    @field_validator("url")
    @classmethod
    def url_must_be_http_url(cls, v) -> str:
        """Validates the input URL and converts it to HttpURL"""
        if not v:
            raise ValueError("URL cannot be None or empty")
        try:
            parsed = HttpUrl(str(v))
            return str(parsed)  # Convert to string immediately
        except Exception as e:
            raise ValueError("Invalid URL. It should start with 'http://' or 'https://'.") from e


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
    created_at: datetime
    config: ContentSourceConfig
    job_id: str | None = None  # Track FireCrawl job
