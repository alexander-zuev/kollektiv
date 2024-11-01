from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pytz import UTC


class WebhookProvider(str, Enum):
    """Supported webhook providers."""

    FIRECRAWL = "firecrawl"
    # Future providers:
    # LLM = "llm"
    # ANALYTICS = "analytics"
    # etc.


class WebhookEventType(str, Enum):
    """Base webhook event types."""

    # FireCrawl events - from docs
    CRAWL_STARTED = "crawl.started"
    CRAWL_PAGE = "crawl.page"
    CRAWL_COMPLETED = "crawl.completed"
    CRAWL_FAILED = "crawl.failed"

    # Future event types:
    # LLM_RESPONSE = "llm.response"
    # ANALYTICS_UPDATE = "analytics.update"
    # etc.


class BaseWebhookEvent(BaseModel):
    """Base model for all webhook events.

    Provides common tracking fields needed across all webhook types.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Internal event tracking ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When the event was received")
    raw_payload: dict[str, Any] = Field(..., description="Original webhook payload for debugging/auditing")

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class FireCrawlWebhookEvent(BaseWebhookEvent):
    """FireCrawl specific webhook event model.

    From FireCrawl docs:
    - success: If the webhook was successful
    - type: The type of event that occurred
    - id: The ID of the crawl
    - data: The data that was scraped (Array). Only non-empty on crawl.page
    - error: If the webhook failed, this will contain the error message
    """

    # Constants/Static values - using Literal instead of const
    provider: Literal[WebhookProvider.FIRECRAWL] = Field(
        WebhookProvider.FIRECRAWL, description="The webhook provider (always FireCrawl for this event type)"
    )

    # Raw FireCrawl fields
    success: bool = Field(True, description="If the webhook was successful")
    type: WebhookEventType = Field(..., description="The type of event that occurred")
    id: str = Field(..., description="The ID of the crawl")
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="The data that was scraped. Only non-empty on crawl.page and will contain 1 item if successful",
    )
    error: str | None = Field(None, description="Error message if the webhook failed")


class WebhookResponse(BaseModel):
    """Standard response model for webhook endpoints.

    Provides consistent response format across all webhook types.
    """

    status: str = Field("success", description="Status of webhook processing")
    message: str = Field(..., description="Human-readable processing result")
    event_id: str = Field(..., description="ID of the processed event")
    provider: WebhookProvider = Field(..., description="Provider that sent the webhook")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the webhook was processed")

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
