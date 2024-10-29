from abc import ABC, abstractmethod

from src.crawling.exceptions import JobNotFoundException
from src.crawling.job_manager import JobManager
from src.crawling.models import WebhookEvent, CrawlJob, WebhookEventType
from src.utils.config import WEBHOOK_URL


class NotificationHandler(ABC):
    @abstractmethod
    async def notify(self, event_type: str, job: CrawlJob) -> None:
        pass

    @abstractmethod
    async def handle_event(self, event: WebhookEvent) -> None:
        pass


class WebhookHandler(NotificationHandler):
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.webhook_url = WEBHOOK_URL


    async def handle_event(self, event: WebhookEvent):
        """Handle the webhook event based on the event status."""

        job_id = event.id

        if event.status == WebhookEventType.STARTED:
            await self.job_manager.start_job(job_id)


        elif event.status == WebhookEventType.COMPLETED:
            result_data = event.data or []
            await self.job_manager.complete_job(job_id, result_data)

        elif event.status == WebhookEventType.FAILED:
            error_message = event.error or "Unknown error"
            await self.job_manager.fail_job(job_id, error_message)