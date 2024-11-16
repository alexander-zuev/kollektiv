from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator

from src.infrastructure.config.settings import settings


class ScrapeOptions(BaseModel):
    """
    Configuration model for web scraping options in the Firecrawl API.

    This model defines various options that control how web pages are scraped,
    including output formats, content filtering, and browser behavior.

    Attributes:
        formats (list[Literal] | None): Output formats, defaults to ["markdown"]
        headers (dict[str, Any] | None): Custom HTTP headers for requests
        include_tags (list[str] | None): HTML tags to include in output
        exclude_tags (list[str] | None): HTML tags to exclude from output, defaults to ["img"]
        only_main_content (bool | None): If True, excludes headers/footers/navigation
        mobile (bool | None): If True, emulates mobile device
        wait_for (int | None): Milliseconds to wait for page load

    Example:
        ```python
        options = ScrapeOptions(formats=["markdown", "html"], only_main_content=True, wait_for=500)
        ```
    """

    formats: list[Literal["markdown", "html", "rawHtml", "links", "screenshot"]] = Field(
        default_factory=lambda: ["markdown"], description="Formats to include in output"
    )
    headers: dict[str, Any] = Field(default_factory=dict)
    include_tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=lambda: ["img"])
    only_main_content: bool = Field(default=True)
    mobile: bool = Field(default=False)
    wait_for: int = Field(default=123)

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Convert to dict with camelCase for API."""
        d = super().dict(*args, exclude_none=True, **kwargs)
        return {
            "formats": d["formats"],
            "headers": d["headers"],
            "includeTags": d["include_tags"],
            "excludeTags": d["exclude_tags"],
            "onlyMainContent": d["only_main_content"],
            "mobile": d["mobile"],
            "waitFor": d["wait_for"],
        }


class CrawlParams(BaseModel):
    """
    Parameter model for configuring web crawling behavior in the Firecrawl API.

    This model defines the configuration for how the crawler should behave,
    including URL patterns, depth limits, and crawling restrictions.

    Attributes:
        url (str): Required. The starting URL for crawling
        exclude_paths (list[str] | None): URL patterns to exclude (regex)
        include_paths (list[str] | None): URL patterns to include (regex)
        max_depth (int | None): Maximum crawl depth from start URL
        ignore_sitemap (bool | None): Whether to ignore site's sitemap
        limit (int | None): Maximum pages to crawl (max 10000)
        allow_backward_links (bool | None): Allow navigation to previous pages
        allow_external_links (bool | None): Allow following external links
        webhook (str | None): Notification webhook URL
        scrape_options (ScrapeOptions | None): Scraping configuration

    Example:
        ```python
        params = CrawlParams(url="https://example.com", max_depth=3, limit=100, exclude_paths=["/blog/*"])
        ```

    Note:
        Only the 'url' field is required. All other fields are optional and will
        use API defaults if not specified.
    """

    url: str = Field(..., description="The base URL to start crawling from")
    exclude_paths: list[str] = Field(default_factory=list, description="URL patterns to exclude from crawl using regex")
    include_paths: list[str] = Field(default_factory=list, description="URL patterns to include in crawl using regex")
    max_depth: int = Field(default=2, ge=1, description="Maximum depth to crawl relative to entered URL")
    ignore_sitemap: bool = Field(default=True, description="Ignore the website sitemap when crawling")
    limit: int = Field(default=10, gt=0, le=10000, description="Maximum number of pages to crawl")
    allow_backward_links: bool = Field(
        default=False, description="Allow crawler to navigate to previously linked pages"
    )
    allow_external_links: bool = Field(default=False, description="Allow crawler to follow external website links")
    webhook: str | None = Field(default=None, description="URL to send webhook notifications")
    scrape_options: ScrapeOptions = Field(default_factory=ScrapeOptions)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format but keep as string."""
        if not v:
            raise ValueError("URL cannot be empty")
        try:
            # Validate format but return string
            parsed = HttpUrl(str(v))
            return str(parsed)
        except Exception as e:
            raise ValueError("Invalid URL format") from e

    @field_validator("webhook")
    @classmethod
    def validate_webhook(cls, v: str | None) -> str | None:
        """Validate webhook URL if provided."""
        if v is not None:
            try:
                parsed = HttpUrl(str(v))
                return str(parsed)
            except Exception as e:
                raise ValueError("Invalid webhook URL format") from e
        return v

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Convert to dict with camelCase for API."""
        d = super().dict(*args, exclude_none=True, **kwargs)
        return {
            "url": d["url"],
            "excludePaths": d["exclude_paths"],
            "includePaths": d["include_paths"],
            "maxDepth": d["max_depth"],
            "ignoreSitemap": d["ignore_sitemap"],
            "limit": d["limit"],
            "allowBackwardLinks": d["allow_backward_links"],
            "allowExternalLinks": d["allow_external_links"],
            "webhook": d["webhook"] if "webhook" in d else None,
            "scrapeOptions": self.scrape_options.dict(),
        }


class CrawlRequest(BaseModel):
    """CrawlRequest model for initiating a web crawl.

    This model handles the initialization and validation of web crawl requests,
    ensuring all parameters are properly formatted and within acceptable ranges.

    Attributes:
        url (HttpUrl): The starting URL for the crawl
        page_limit (int): Max pages to crawl (1-1000, default: DEFAULT_PAGE_LIMIT)
        max_depth (int): Max crawl depth (1-10, default: DEFAULT_MAX_DEPTH)
        exclude_patterns (list[str]): URL patterns to exclude (e.g., '/blog/*')
        include_patterns (list[str]): URL patterns to include (e.g., '/api/*')
        time_taken (float | None): Total crawl duration in seconds
        webhook_url (HttpUrl | None): Optional webhook for status updates

    Validators:
        - Ensures URL is valid and ends with a slash
        - Validates pattern formats for include/exclude patterns
        - Enforces limits on page count and crawl depth

    Example:
        ```python
        request = CrawlRequest(url="https://example.com", page_limit=100, max_depth=3, exclude_patterns=["/private/*"])
        ```
    """

    url: str = Field(..., description="The starting URL of the crawl request.")
    page_limit: int = Field(
        default=settings.default_page_limit,
        gt=0,
        le=1000,
        description="Maximum number of pages to crawl. Maximum is 1000.",
    )
    max_depth: int = Field(
        default=settings.default_max_depth,
        gt=0,
        le=10,
        description="Maximum depth for crawling",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="The list of patterns to exclude, e.g., '/blog/*', '/author/*'.",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="The list of patterns to include, e.g., '/blog/*', '/api/*'.",
    )
    time_taken: float | None = Field(default=0.0, description="The time taken to crawl this request end to end.")
    webhook_url: str | None = Field(default=None, description="Optional webhook URL for updates")

    @field_validator("url", "webhook_url")
    @classmethod
    def url_must_be_http_url(cls, v: str | HttpUrl) -> str:
        """Validates the input URL and webhook and converts it to str"""
        if not v:
            raise ValueError("URL cannot be None or empty")
        try:
            parsed = HttpUrl(str(v))
            return str(parsed)
        except Exception as e:
            raise ValueError(f"Invalid URL format for: {v}") from e

    @field_validator("url")
    @classmethod
    def url_must_end_with_slash(cls, url: str | HttpUrl) -> str:
        """Ensures that start URL always with a trailing slash"""
        if not url:
            raise ValueError("URL cannot be None or empty")

        url = str(url)
        if not url.endswith("/"):
            url += "/"
        return url

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

    def __repr__(self) -> str:
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
    r"""
    Model for storing and validating crawled page data.

    This model ensures that crawled data meets the required structure and
    contains all necessary information for each crawled page.

    Attributes:
        data (list[dict[str, Any]]): List of page data objects, each containing:
            - markdown (str): Page content in markdown format
            - metadata (dict): Additional page information

    Validators:
        - Ensures data list is not empty
        - Validates presence of required keys in each data item
        - Checks that markdown content is non-null and properly formatted

    Example:
        ```python
        crawl_data = CrawlData(
            data=[{"markdown": "# Page Title\nContent...", "metadata": {"url": "https://example.com/page"}}]
        )
        ```
    """

    data: list[dict[str, Any]] = Field(default_factory=list, description="List of page data objects from FireCrawl")

    @field_validator("data")
    def validate_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:  # noqa: N805
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
            if "markdown" not in item:
                raise ValueError("Missing 'markdown' key in data")
            if "metadata" not in item:
                raise ValueError("Missing 'metadata' key in data")

            # Validate markdown
            if item["markdown"] is None or not isinstance(item["markdown"], str):
                raise ValueError("Markdown must be a non-null string")
        return v

    def __len__(self) -> int:
        """Return the length of the data list."""
        return len(self.data)


# Crawl Result
class CrawlResult(BaseModel):
    """
    Model representing the complete result of a web crawl operation.

    This model contains all information about a completed crawl job,
    including status, statistics, and collected data.

    Attributes:
        job_status (CrawlJobStatus): Current status of the crawl job
        input_url (str): Original URL that was crawled
        total_pages (int): Number of successfully crawled pages
        unique_links (list[str]): All unique URLs discovered
        data (CrawlData): Collected page content and metadata
        completed_at (datetime | None): Completion timestamp (UTC)
        error_message (str | None): Error details if job failed
        filename (str | None): Name of saved results file
        method (str): API method used ("crawl" by default)

    Example:
        ```python
        result = CrawlResult(
            job_status=JobStatus.COMPLETED,
            input_url="https://example.com",
            total_pages=42,
            data=crawl_data,
            completed_at=datetime.now(UTC),
        )
        ```
    """

    result_id: UUID = Field(default_factory=lambda: uuid4(), description="System generated UUID of the crawl result.")
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

    class Config:
        """Configuration class for CrawlResult model."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        extra = "allow"
        validate_assignment = True


class FireCrawlResponse(BaseModel):
    """Object encapsulating response from FireCrawl async_crawl_url."""

    success: bool = Field(..., description="Indicates if the crawl initiation was successful.")
    job_id: str = Field(..., description="The unique identifier for the crawl job.")
    url: str = Field(..., description="The URL to check the status of the crawl job.")

    @classmethod
    def from_firecrawl_response(cls, response: dict[str, Any]) -> "FireCrawlResponse":
        """Converts a Firecrawl API response dictionary to a FireCrawlResponse object."""
        return cls(success=response["success"], job_id=response["id"], url=response["url"])
