from typing import Any

from src.api.v0.schemas.webhook_schemas import (
    FireCrawlEvent,
    FireCrawlEventType,
    FireCrawlWebhookEvent,
    WebhookProvider,
    WebhookResponse,
)


class FireCrawlWebhookHandler:
    """Handles FireCrawl webhook processing logic."""

    @staticmethod
    def _create_firecrawl_event(data: dict[str, Any]) -> FireCrawlEvent:
        """Create FireCrawl event from webhook data.

        Raises:
            ValueError: If required fields are missing
        """
        try:
            return FireCrawlEvent(
                success=data["success"],
                event_type=FireCrawlEventType(data["event_type"]) if "event_type" in data else None,
                crawl_id=data["crawl_id"],  # We expect crawl_id as per schema
                data=data.get("data", []),
                error=data.get("error"),
            )
        except KeyError as e:
            # Convert to ValueError for better error handling
            raise ValueError(f"Missing required field: {e.args[0]}")

    @staticmethod
    def _create_webhook_event(event_data: FireCrawlEvent, raw_payload: dict[str, Any]) -> FireCrawlWebhookEvent:
        """Create webhook event wrapper."""
        return FireCrawlWebhookEvent(provider=WebhookProvider.FIRECRAWL, raw_payload=raw_payload, data=event_data)

    @staticmethod
    def _create_webhook_response(event: FireCrawlWebhookEvent) -> WebhookResponse:
        """Create standardized webhook response."""
        return WebhookResponse(
            event_id=event.event_id,
            message=f"Processed {event.data.event_type} event for job {event.data.crawl_id}",
            provider=WebhookProvider.FIRECRAWL,
        )
