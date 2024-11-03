from abc import ABC, abstractmethod

from src.models.common.webhook import WebhookEvent


class BaseWebhookHandler(ABC):
    @abstractmethod
    async def handle_event(self, event: WebhookEvent) -> None:
        """Handle a webhook event"""
        pass
