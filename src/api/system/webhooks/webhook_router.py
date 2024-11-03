from fastapi import APIRouter, HTTPException, Request

from src.api.routes import Routes
from src.crawling.webhook_handler import WebhookHandler
from src.models.common.webhooks import FireCrawlWebhookEvent, WebhookProvider, WebhookResponse
from src.utils.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.post(
    Routes.System.Webhooks.FIRECRAWL, response_model=WebhookResponse, description="Handle FireCrawl webhook callbacks"
)
async def handle_firecrawl_webhook(request: Request) -> WebhookResponse:
    """Handle FireCrawl webhook callbacks."""
    try:
        # Get raw payload
        data = await request.json()
        logger.debug(f"Received FireCrawl webhook data: {data}")

        # Create FireCrawl event
        event = FireCrawlWebhookEvent(
            raw_payload=data,
            type=data["type"],
            id=data["id"],
            success=data.get("success", True),
            error=data.get("error"),
            data=data.get("data", []),
        )

        logger.info(f"Processing FireCrawl webhook event: {event.type} for job {event.id}")

        webhook_handler: WebhookHandler = request.app.state.webhook_handler
        await webhook_handler.handle_event(event)

        return WebhookResponse(
            status="success",
            message=f"Processed {event.type} event for job {event.id}",
            event_id=event.event_id,
            provider=WebhookProvider.FIRECRAWL,
        )

    except Exception as e:
        logger.error(f"FireCrawl webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
