"""Event types for chat operations."""
from enum import Enum
from typing import Any
from dataclasses import dataclass
from typing import Optional


class StandardEventType(str, Enum):
    """Standard event types for chat operations."""

    MESSAGE_START = "message_start"
    TEXT_TOKEN = "text_token"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    MESSAGE_COMPLETE = "message_complete"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
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


@dataclass
class ChatEvent:
    """Base class for all chat events."""
    message_id: str

    def to_standard_event(self) -> StandardEvent:
        """Convert to StandardEvent format for backward compatibility."""
        raise NotImplementedError


@dataclass
class MessageStartEvent(ChatEvent):
    """Event emitted when a message starts."""

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content={"message_id": self.message_id}
        )


@dataclass
class ContentBlockEvent(ChatEvent):
    """Event emitted for each content block in a message."""
    text: str
    content_block_id: str

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.TEXT_TOKEN,
            content=self.text
        )


@dataclass
class MessageEndEvent(ChatEvent):
    """Event emitted when a message ends."""
    end_reason: str
    model: str

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.MESSAGE_STOP,
            content={"message_id": self.message_id, "model": self.model}
        )


@dataclass
class ErrorEvent(ChatEvent):
    """Event emitted when an error occurs."""
    error_type: str
    error_message: str
    recoverable: bool = False

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.ERROR,
            content={
                "message_id": self.message_id,
                "error_type": self.error_type,
                "error_message": self.error_message,
                "recoverable": self.recoverable
            }
        )
