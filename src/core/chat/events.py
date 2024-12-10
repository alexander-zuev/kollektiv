"""Event types for chat operations."""
from enum import Enum


class StandardEventType(str, Enum):
    """Standard event types for chat operations."""

    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    ERROR = "error"
    DONE = "done"


class StreamEvent:
    """Base class for stream events."""

    def __init__(self, event_type: StandardEventType, data: dict):
        """Initialize stream event."""
        self.event_type = event_type
        self.data = data

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "type": self.event_type,
            "data": self.data
        }
