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
        return FireCrawlEvent(
            success=data["success"],
            event_type=FireCrawlEventType(data["type"]),
            crawl_id=data["id"],
            data=data.get("data", []),
            error=data.get("error"),
        )

    @staticmethod
    def _create_webhook_event(event_data: FireCrawlEvent, raw_payload: dict[str, Any]) -> FireCrawlWebhookEvent:
        return FireCrawlWebhookEvent(
            provider=WebhookProvider.FIRECRAWL,
            raw_payload=raw_payload,
            data=event_data,
        )

    @staticmethod
    def _create_webhook_response(event: FireCrawlWebhookEvent) -> WebhookResponse:
        return WebhookResponse(
            event_id=event.event_id,
            message=f"Processed {event.data.event_type} event for job {event.data.crawl_id}",
            provider=WebhookProvider.FIRECRAWL,
        )
