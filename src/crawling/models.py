from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, ValidationInfo, field_validator

from src.utils.config import DEFAULT_MAX_DEPTH, DEFAULT_PAGE_LIMIT


# CRAWLING
class CrawlRequest(BaseModel):
    """
    CrawlRequest model for initiating a web crawl.

    Attributes:
        url (HttpUrl): The starting URL of the crawl request.
        page_limit (int): Maximum number of pages to crawl. Maximum is 1000.
        max_depth (int): Maximum depth for crawling. Default is 5, with a range of 1 to 10.
        exclude_patterns (list[str]): The list of patterns to exclude, e.g., '/blog/*', '/author/*'.
        include_patterns (list[str]): The list of patterns to include, e.g., '/blog/*', '/api/*'.

    Methods:
        url_must_be_http_url(cls, v):
            Validates that the URL is a valid HttpUrl.

        validate_patterns(cls, v: list[str]) -> list[str]:
            Validates that the patterns in exclude_patterns and include_patterns are properly formatted.

    Config:
        arbitrary_types_allowed (bool): Configuration option to allow arbitrary types.
    """

    url: HttpUrl = Field(..., description="The starting URL of the crawl request.")
    page_limit: int = Field(
        default=DEFAULT_PAGE_LIMIT, gt=0, le=1000, description="Maximum number of pages to crawl. Maxium"
    )
    max_depth: int = Field(
        default=DEFAULT_MAX_DEPTH,
        gt=0,
        le=10,
        description="Maximum depth for crawling",  # Move from hardcoded in async_crawl_url
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="The list of str of patterns to "
        "exclude. For "
        "example, "
        "/blog/*, /author/. Delimited by a comma",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="The list of str of patterns to "
        "include. For "
        "example, "
        "/blog/*, /api/. Delimited by a comma",
    )
    time_taken: float | None = Field(None, description="The time taken to crawl this request end to end.")
    webhook_url: HttpUrl | None = None  # Optional webhook URL for updates

    @field_validator("url")
    @classmethod
    def url_must_be_http_url(cls, v):
        """Validates the input URL and converts it to HttpURL"""
        if not v:
            raise ValueError("URL cannot be None or empty")
        try:
            parsed = HttpUrl(str(v))
            return str(parsed)  # Convert to string immediately
        except Exception as e:
            raise ValueError("Invalid URL. It should start with 'http://' or 'https://'.") from e

    @field_validator("url")
    @classmethod
    def url_must_end_with_slash(cls, url):
        """Ensures that start URL always with a trailing slash"""
        if not url:
            raise ValueError("URL cannot be None or empty")

        url = str(url)
        if not url.endswith("/"):
            url += "/"
        return url

    @field_validator("exclude_patterns", "include_patterns")
    def validate_patterns(cls, v: list[str]) -> list[str]:
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

    def __repr__(self):
        """Returns a detailed string representation of the CrawlRequest."""
        patterns = []
        if self.include_patterns:
            patterns.append(f"include: {self.include_patterns}")
        if self.exclude_patterns:
            patterns.append(f"exclude: {self.exclude_patterns}")
        patterns_str = f", patterns: [{', '.join(patterns)}]" if patterns else ""

        return (
            f"CrawlRequest(url: {self.url}, "
            f"page_limit: {self.page_limit}, "
            f"max_depth: {self.max_depth}"
            f"{patterns_str})"
        )

    class Config:
        """Configuration class for CrawlRequest model."""

        arbitrary_types_allowed = True


class CrawlData(BaseModel):
    """
    CrawlData

    A class that represents the data structure for crawling page data. This class
    inherits from BaseModel and is designed to ensure that the data provided
    conforms to the required structure and constraints.

    Attributes:
        data (list[dict[str, Any]]): List of page data objects from FireCrawl,
            each containing 'markdown' and 'metadata' keys.

    Methods:
        validate_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
            Validates the 'data' field to make sure it meets the specified requirements.
            Ensures 'data' is not empty, and each item in 'data' is a dictionary
            containing 'markdown' and 'metadata' keys, with 'markdown' not being None.
    """

    data: list[dict[str, Any]] = Field(
        ..., default_factory=list, description="List of page data objects from " "FireCrawl"
    )

    @field_validator("data")
    def validate_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """

        Validates the field 'data' for the given class.

        Args:
            cls: The class of which the field is being validated.
            v (list[dict[str, Any]]): A list of dictionaries to be validated.

        Returns:
            list[dict[str, Any]]: The validated list of dictionaries.

        Raises:
            ValueError: If the input list is empty.
            ValueError: If an item in the list is not a dictionary.
            ValueError: If a dictionary item is missing the 'markdown' key.
            ValueError: If a dictionary item is missing the 'metadata' key.
            ValueError: If the value associated with the 'markdown' key is None.

        """
        if not v:
            raise ValueError("Data must not be empty")
        for item in v:
            if not isinstance(item, dict):
                raise ValueError(f"Expected dict, got {type(item)}")
            if "markdown" not in item:
                raise ValueError("Missing 'markdown' key in data")
            if "metadata" not in item:
                raise ValueError("Missing 'metadata' key in data")

            # Validate markdown
            if item["markdown"] is None or not isinstance(item["markdown"], str):
                raise ValueError("Markdown must be a non-null string")
        return v

    def __len__(self):
        """Return the length of the data list."""
        return len(self.data)


class CrawlResult(BaseModel):
    """
    Represents the result of a web crawling job, containing metadata and discovered data.

    Attributes:
        job_status (CrawlJobStatus): The status of the crawl job.
        input_url (str): The original URL that was crawled.
        total_pages (int): Total number of pages successfully crawled. Must be non-negative.
        unique_links (list[str]): List of unique URLs discovered during crawling. Defaults to an empty list.
        data (list[CrawlData]): The actual crawled data from all pages.
        completed_at (datetime | None): When the crawl job completed. Defaults to the current UTC datetime.
        error_message (str | None): Error message if the crawl failed. Defaults to None.

    Methods:
        validate_data_length(cls, v, values): Ensures the total_pages matches the length of the data list.

    Config:
        json_encoders (dict): Allows converting datetime to ISO format in JSON.
        extra (str): Allows extra fields in input data. Set to "allow".
        validate_assignment (bool): Validates whenever a field is set. Set to True.
    """

    job_status: "CrawlJobStatus" = Field(...)
    input_url: str = Field(..., description="The original URL that was crawled")
    total_pages: int = Field(..., ge=0, description="Total number of pages successfully crawled")
    unique_links: list[str] = Field(default_factory=list, description="List of unique URLs discovered during crawling")
    data: CrawlData = Field(...)
    completed_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), description="When the crawl job completed"
    )
    error_message: str | None = Field(None, description="Error message if the crawl failed")
    filename: str | None = Field(None, description="Filename of the saved results")
    method: str = Field(default="crawl", description="Firecrawl API method used")

    # @field_validator("data")
    # def validate_data_length(cls, v: list[CrawlData], values: dict) -> list[CrawlData]:
    #     """Ensure total_pages matches data length"""
    #     if len(v) != values.get("total_pages", 0):
    #         raise ValueError(f"Data length {len(v)} does not match total_pages {values.get('total_pages')}")
    #     return v

    class Config:
        """Configuration class for CrawlResult model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        extra = "allow"
        validate_assignment = True


# JOBS
class CrawlJobStatus(str, Enum):
    """

    Represents the status of a web crawling job.

    Attributes:
        COMPLETED (str): Indicates that the crawl job has completed successfully.
        FAILED (str): Indicates that the crawl job has failed.
        IN_PROGRESS (str): Indicates that the crawl job is currently in progress.
        PENDING (str): Indicates that the crawl job is pending and has not yet been started.
        CANCELLED (str): Indicates the job was cancelled by the user.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# 2. Concrete job object that tracks everything we care about
class CrawlJob(BaseModel):
    """Track crawl job status and progress"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    firecrawl_id: str
    status: CrawlJobStatus
    start_url: str
    method: str = Field(default="crawl")

    # Progress tracking
    total_pages: int | None = None
    pages_crawled: int = 0
    progress_percentage: float = 0.0

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results reference only
    result_file: str | None = None
    error: str | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Webhook models


class WebhookEventType(str, Enum):
    """FireCrawl webhook event types"""

    STARTED = "crawl.started"
    PAGE = "crawl.page"
    COMPLETED = "crawl.completed"
    FAILED = "crawl.failed"


class WebhookEvent(BaseModel):
    """Firecrawl webhook event model.

    This class represents webhook events received from the FireCrawl API,
    including progress updates and completion notifications.

    Attributes:
        id (str): Unique identifier for the webhook event.
        type (WebhookEventType): Type of the webhook event.
        success (bool): Whether the event represents a successful operation.
        error (str | None): Error message if the event represents a failure.
        completed (int | None): Number of pages crawled (for page events).
        total (int | None): Total pages to crawl (for page events).
    """

    id: str
    type: WebhookEventType
    success: bool = True
    error: str | None = None

    # Progress information for page events
    completed: int | None = None  # Number of pages crawled
    total: int | None = None  # Total pages to crawl

    @field_validator("completed", "total")
    @classmethod
    def validate_progress(cls, v: int | None, info: ValidationInfo) -> int | None:
        """Validate progress information for page events.

        Args:
            v (int | None): The value to validate.
            info (ValidationInfo): Validation context information.

        Returns:
            int | None: The validated value.

        Raises:
            ValueError: If validation fails for page events.
        """
        if info.data.get("type") == WebhookEventType.PAGE:
            if v is None:
                raise ValueError("Page events must include progress information")
            if v < 0:
                raise ValueError("Progress values cannot be negative")
        return v
