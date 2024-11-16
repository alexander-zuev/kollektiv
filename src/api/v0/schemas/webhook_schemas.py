from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pytz import UTC

T_WebhookData = TypeVar("T_WebhookData", bound=BaseModel)


class WebhookProvider(str, Enum):
    """Supported webhook providers."""

    FIRECRAWL = "firecrawl"


class WebhookEvent(BaseModel, Generic[T_WebhookData]):
    """Base model for all webhook events.

    Provides common tracking fields needed across all webhook types.

    """

    event_id: UUID = Field(default_factory=lambda: uuid4(), description="Internal event tracking ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When the event was received")
    raw_payload: dict = Field(..., description="Original webhook payload")
    data: T_WebhookData = Field(..., description="Processed event data. Must be defined for each provider")
    provider: WebhookProvider = Field(..., description="The webhook provider")

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class FireCrawlEventType(str, Enum):
    """Base webhook event types."""

    # FireCrawl events - from docs
    CRAWL_STARTED = "crawl.started"
    CRAWL_PAGE = "crawl.page"
    CRAWL_COMPLETED = "crawl.completed"
    CRAWL_FAILED = "crawl.failed"


class FireCrawlWebhookResponse(BaseModel):
    """FireCrawl specific webhook response model.

    From FireCrawl docs:
    - success: If the webhook was successful
    - event_type: The type of event that occurred
    - firecrawl_id: The ID of the crawl (mapped from 'id' in the webhook)
    - data: The data that was scraped (Array). Only non-empty on crawl.page
    - error: If the webhook failed, this will contain the error message
    """

    # Aligned with FireCrawl Webhook Response https://docs.firecrawl.dev/features/crawl#webhook-events
    success: bool = Field(True, description="If the webhook was successful in crawling the page correctly.")
    event_type: FireCrawlEventType = Field(..., description="The type of event that occurred")
    firecrawl_id: str = Field(..., alias="id", description="The ID of the crawl")
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="The data that was scraped (Array). This will only be non empty on crawl.page and will contain 1 "
        " item if the page was scraped successfully. The response is the same as the /scrape endpoint.",
    )
    error: str | None = Field(None, description="If the webhook failed, this will contain the error message.")

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True


class WebhookResponse(BaseModel):
    """Standard response model for webhook endpoints.

    Provides consistent response format across all webhook types.
    """

    status: str = Field("success", description="Status of webhook processing")
    message: str = Field(..., description="Human-readable processing result")
    event_id: UUID = Field(..., description="ID of the processed event")
    provider: WebhookProvider = Field(..., description="Provider that sent the webhook")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the webhook was processed")

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class FireCrawlWebhookEvent(WebhookEvent[FireCrawlWebhookResponse]):
    """Concrete webhook event type for FireCrawl."""

    pass
