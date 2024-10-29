from fastapi import FastAPI, HTTPException, APIRouter, Request
from src.crawling.models import WebhookEvent
from src.crawling.webhook_handler import WebhookHandler
from src.crawling.job_manager import JobManager
from src.utils.logger import get_logger

from src.utils.config import WEBHOOK_PATH, JOB_FILE_DIR

logger = get_logger()

# Create FastAPI app for webhooks only
router = APIRouter()

# Initialize webhook handler
job_manager = JobManager(JOB_FILE_DIR)
webhook_handler = WebhookHandler(job_manager)



@router.post(WEBHOOK_PATH)
async def handle_webhook(request: Request):
    """Handle FireCrawl webhook events"""
    try:
        data = await request.json()
        event = WebhookEvent(**data)
        await webhook_handler.handle_event(event)
        return {"status": "Webhook request received."}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))