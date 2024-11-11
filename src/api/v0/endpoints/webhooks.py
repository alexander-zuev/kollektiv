from fastapi import APIRouter, HTTPException, Request, status

from src.api.dependencies import ContentServiceDep
from src.api.routes import Routes
from src.api.v0.schemas.webhook_schemas import WebhookResponse
from src.infrastructure.config.logger import get_logger
from src.services.webhook_handler import FireCrawlWebhookHandler

logger = get_logger()
router = APIRouter()

print("Starting webhook routes init")


@router.post(
    path=Routes.System.Webhooks.FIRECRAWL,
    response_model=None,
    status_code=status.HTTP_200_OK,
    description="Handle FireCrawl webhook callbacks",
)
async def handle_firecrawl_webhook(
    request: Request, content_service: ContentServiceDep
) -> WebhookResponse | HTTPException:
    """Handle FireCrawl webhook callbacks.

    Args:
        request: The incoming webhook request
        content_service: Injected content service dependency

    Returns:
        WebhookResponse: Response indicating successful processing

    Raises:
        HTTPException: If webhook processing fails
    """
    logger.debug(f"Receiving webhook at: {request.url}")
    try:
        handler = FireCrawlWebhookHandler()

        # Get raw payload
        raw_payload = await request.json()
        logger.debug(f"Received FireCrawl webhook data: {raw_payload}")

        # Create FireCrawl event
        event_data = handler._create_firecrawl_event(data=raw_payload)

        # Create FireCrawlWebhookEvent
        event = handler._create_webhook_event(event_data=event_data, raw_payload=raw_payload)

        # Call ContentService with CrawlEvent
        await content_service.handle_event(event=event)

        # Construct and return WebhookResponse
        return handler._create_webhook_response(event=event)

    except Exception as e:
        logger.error(f"FireCrawl webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e
