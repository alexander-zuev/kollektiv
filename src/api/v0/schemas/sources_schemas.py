from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator

from src.models.base_models import SupabaseModel
from src.models.content_models import DataSource, DataSourceType, SourceStatus


class ContentSourceConfig(BaseModel):
    """Configuration parameters for a content source."""

    url: str = Field(..., description="Base URL of the content to crawl.")
    page_limit: int = Field(default=50, gt=0, description="Maximum number of pages to crawl.")
    exclude_patterns: list[str] = Field(
        default_factory=list,
        alias="excludePaths",
        description="The list of patterns to exclude, e.g., '/blog/*', '/author/*'.",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        alias="includePaths",
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


class AddContentSourceRequest(SupabaseModel):
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


class SourceAPIResponse(BaseModel):
    """Simplified model inheriting from Source."""

    source_id: UUID = Field(...)
    source_type: DataSourceType = Field(..., description="Data source type")
    status: SourceStatus = Field(..., description="Status of the data source")
    created_at: datetime = Field(..., description="Date timestamp in UTC when data source was created.")
    error: str | None = Field(None, description="Error message, null if no error")

    @classmethod
    def from_source(cls, source: DataSource) -> "SourceAPIResponse":
        return cls(
            source_id=source.source_id,
            status=source.status,
            source_type=source.source_type,
            created_at=source.created_at,
        )
