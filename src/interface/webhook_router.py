from fastapi import APIRouter, HTTPException, Request

from src.crawling.job_manager import JobManager
from src.crawling.models import WebhookEvent
from src.crawling.webhook_handler import WebhookHandler
from src.utils.config import JOB_FILE_DIR, WEBHOOK_PATH
from src.utils.logger import get_logger

logger = get_logger()
router = APIRouter()

# Initialize components
job_manager = JobManager(JOB_FILE_DIR)
webhook_handler = WebhookHandler(job_manager)


@router.post(WEBHOOK_PATH)
async def handle_webhook(request: Request):
    """Handle Firecrawl webhook events."""
    try:
        data = await request.json()
        logger.debug(f"Received webhook data: {data}")

        event = WebhookEvent(**data)
        logger.info(f"Processing webhook event: {event.type} for job {event.id}")

        await webhook_handler.handle_event(event)
        return {"status": "success", "message": f"Processed {event.type} event"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
