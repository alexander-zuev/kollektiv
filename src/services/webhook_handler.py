from typing import Any

from src.api.v0.schemas.webhook_schemas import (
    FireCrawlWebhookEvent,
    FireCrawlWebhookResponse,
    WebhookProvider,
    WebhookResponse,
)


class FireCrawlWebhookHandler:
    """Handles FireCrawl webhook processing logic."""

    @staticmethod
    def _parse_firecrawl_payload(data: dict[str, Any]) -> FireCrawlWebhookResponse:
        """Parse FireCrawl webhook payload into a structured response object.

        Args:
            data: Raw webhook payload from FireCrawl

        Raises:
            ValueError: If required fields are missing
        """
        try:
            return FireCrawlWebhookResponse(
                success=data["success"],
                event_type=data["type"],
                firecrawl_id=data["id"],
                data=data.get("data", []),
                error=data.get("error"),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e.args[0]}") from e

    @staticmethod
    def _create_webhook_event(
        event_data: FireCrawlWebhookResponse, raw_payload: dict[str, Any]
    ) -> FireCrawlWebhookEvent:
        """Create internal webhook event from parsed payload."""
        return FireCrawlWebhookEvent(provider=WebhookProvider.FIRECRAWL, raw_payload=raw_payload, data=event_data)

    @staticmethod
    def _create_webhook_response(event: FireCrawlWebhookEvent) -> WebhookResponse:
        """Create API response for the webhook sender."""
        return WebhookResponse(
            event_id=event.event_id,
            message=f"Processed {event.data.event_type} event for job {event.data.firecrawl_id}",
            provider=WebhookProvider.FIRECRAWL,
        )
