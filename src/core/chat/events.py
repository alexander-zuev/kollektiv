"""Event types for chat operations."""
from enum import Enum
from typing import Any


class StandardEventType(str, Enum):
    """Standard event types for chat operations."""

    MESSAGE_START = "message_start"
    TEXT_TOKEN = "text_token"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"
    DONE = "done"


class StandardEvent:
    """Standard event for chat operations."""

    def __init__(self, event_type: StandardEventType, content: Any):
        """Initialize standard event.

        Args:
            event_type: Type of the event.
            content: Event content, can be any type depending on the event type.
        """
        self.event_type = event_type
        self.content = content
