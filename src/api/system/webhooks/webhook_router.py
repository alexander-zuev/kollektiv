from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from src.api.deps import ContentServiceDep
from src.api.routes import Routes
from src.infrastructure.config.logger import get_logger
from src.models.common.webhook_models import (
    FireCrawlEvent,
    FireCrawlEventType,
    WebhookEvent,
    WebhookProvider,
    WebhookResponse,
)

logger = get_logger()
router = APIRouter()


@router.post(
    Routes.System.Webhooks.FIRECRAWL,
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    description="Handle FireCrawl webhook callbacks",
)
async def handle_firecrawl_webhook(request: Request, content_service: ContentServiceDep) -> WebhookResponse:
    """Thin API layer for webhook handling.

    - Validates requests
    - Transforms to domain events
    - Routes to appropriate service
    - Handles responses/errors
    """
    try:
        # Get raw payload
        data = await request.json()
        logger.debug(f"Received FireCrawl webhook data: {data}")

        # Create FireCrawl event
        event_data = FireCrawlEvent(
            success=data["success"],
            event_type=FireCrawlEventType(data["type"]),  # Convert to enum
            crawl_id=data["id"],
            data=data.get("data", []),
            error=data.get("error"),
        )

        event = WebhookEvent[FireCrawlEvent](
            provider=WebhookProvider.FIRECRAWL,
            raw_payload=data,
            data=event_data,
        )

        logger.info(f"Processing FireCrawl webhook event: {event_data.event_type} for job " f" {event_data.crawl_id}")

        # Call ContentService with CrawlEvent
        await content_service.handle_event(event=event)

        # Construct and return WebhookResponse
        return WebhookResponse(
            event_id=event.event_id,
            message=f"Processed {event_data.event_type} event for job {event_data.crawl_id}",
            provider=WebhookProvider.FIRECRAWL,
            # timestamp will be added automatically by the model
        )

    except Exception as e:
        logger.error(f"FireCrawl webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
