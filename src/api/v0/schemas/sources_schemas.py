from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from src.models.content.content_source_models import DataSourceType, Source, SourceStatus


class ContentSourceType(str, Enum):
    """Supported content source types."""

    WEB = "web"  # Web crawling
    # Future: CONFLUENCE = "confluence"  # Future: Confluence integration
    # Future: JIRA = "jira"  # Future: Jira integration
    # Future: GITHUB = "github"  # Future: GitHub docs/wikis


class ContentSourceConfig(BaseModel):
    """Configuration parameters for a content source."""

    url: str = Field(..., description="Base URL of the content to crawl.")
    page_limit: int = Field(default=50, gt=0, description="Maximum number of pages to crawl.")
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="The list of patterns to exclude, e.g., '/blog/*', '/author/*'.",
    )
    include_patterns: list[str] = Field(
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

    @field_validator("exclude_patterns", "include_patterns")
    def validate_patterns(cls, v: list[str]) -> list[str]:  # noqa: N805
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


class AddContentSourceRequest(BaseModel):
    """Request to add a new content source."""

    source_type: ContentSourceType = Field(
        ..., description="Type of content source (currently only 'web' is supported)."
    )
    config: ContentSourceConfig

    class Config:
        """Example config."""

        json_schema_extra = {
            "example": {
                "source_type": "web",
                "config": {
                    "url": "https://docs.example.com",
                    "max_pages": 50,
                    "exclude_paths": ["/blog/*"],
                },
            }
        }


class SourceAPIResponse(BaseModel):
    """Simplified model inheriting from Source."""

    source_id: UUID = Field(...)
    source_type: DataSourceType = Field(..., description="Data source type")
    status: SourceStatus = Field(..., description="Status of the data source")
    created_at: datetime = Field(..., description="Date timestamp in UTC when data source was created.")
    error: str | None = Field(None, description="Error message, null if no error")

    @classmethod
    def from_source(cls, source: Source) -> "SourceAPIResponse":
        return cls(
            source_id=source.source_id,
            status=source.status,
            source_type=source.source_type,
            created_at=source.created_at,
        )
