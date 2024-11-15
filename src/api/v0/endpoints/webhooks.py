from fastapi import APIRouter, HTTPException, Request, status

from src.api.dependencies import ContentServiceDep
from src.api.routes import Routes
from src.api.v0.schemas.webhook_schemas import WebhookResponse
from src.infrastructure.config.logger import get_logger
from src.services.webhook_handler import FireCrawlWebhookHandler

logger = get_logger()
router = APIRouter()


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
        HTTPException: 400 if webhook payload is invalid
        HTTPException: 500 if processing fails for other reasons
    """
    logger.debug(f"Receiving webhook at: {request.url}")
    try:
        handler = FireCrawlWebhookHandler()

        # Get raw payload
        raw_payload = await request.json()
        logger.debug(f"Received FireCrawl webhook data: {raw_payload}")

        try:
            # Create FireCrawl event - this may raise ValueError for validation
            event_data = handler._create_firecrawl_event(data=raw_payload)
        except ValueError as ve:
            # Handle validation errors with 400
            logger.warning(f"Invalid webhook payload: {str(ve)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {str(ve)}"
            ) from ve

        # Create FireCrawlWebhookEvent
        event = handler._create_webhook_event(event_data=event_data, raw_payload=raw_payload)

        try:
            # Call ContentService with CrawlEvent
            await content_service.handle_event(event=event)
            logger.debug("Successfully sent event to the ContentService")
        except Exception as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing webhook: {str(e)}"
            ) from e

        # Construct and return WebhookResponse
        return handler._create_webhook_response(event=event)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in webhook handler: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        ) from e
