"""Chat event types for streaming responses."""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core._exceptions import StreamingError, TokenLimitError, ClientDisconnectError


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


class ChatEvent(BaseModel):
    """Base class for all chat events."""

    message_id: str = Field(..., description="ID of the message this event belongs to")

    def to_standard_event(self) -> StandardEvent:
        """Convert to StandardEvent format for backward compatibility."""
        raise NotImplementedError


class MessageStartEvent(ChatEvent):
    """Event indicating the start of a message."""

    model: Optional[str] = Field(None, description="Model used for generating the response")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.MESSAGE_START, content={"message_id": self.message_id, "model": self.model}
        )


class ContentBlockEvent(ChatEvent):
    """Event containing a content block."""

    text: str = Field(..., description="Text content of the block")
    content_block_id: str = Field(..., description="ID of the content block")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(event_type=StandardEventType.TEXT_TOKEN, content=self.text)


class MessageStopEvent(ChatEvent):
    """Event indicating the end of a message."""

    end_reason: str = Field(..., description="Reason for message completion")
    model: str = Field(..., description="Model used for generating the response")
    usage: Dict[str, Any] = Field(..., description="Token usage information")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.MESSAGE_STOP,
            content={"message_id": self.message_id, "model": self.model, "usage": self.usage},
        )


class ErrorEvent(ChatEvent):
    """Event indicating an error occurred."""

    error_type: str = Field(..., description="Type of error that occurred")
    error_message: str = Field(..., description="Error message")
    recoverable: bool = Field(default=False, description="Whether the error is recoverable")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.ERROR,
            content={
                "message_id": self.message_id,
                "error_type": self.error_type,
                "error_message": self.error_message,
                "recoverable": self.recoverable,
            },
        )


class ToolStartEvent(ChatEvent):
    """Event indicating the start of tool use."""

    tool_name: str = Field(..., description="Name of the tool being used")
    tool_input: Dict[str, Any] = Field(..., description="Input parameters for the tool")
    tool_use_id: str = Field(..., description="ID of the tool use")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.TOOL_START,
            content={
                "message_id": self.message_id,
                "tool_name": self.tool_name,
                "tool_input": self.tool_input,
                "tool_use_id": self.tool_use_id,
            },
        )


class ToolResultEvent(ChatEvent):
    """Event containing tool execution result."""

    tool_use_id: str = Field(..., description="ID of the tool use")
    content: Optional[str | Dict[str, Any]] = Field(None, description="Result returned from the tool")
    is_error: bool = Field(default=False, description="Whether the result is an error")


class ToolEndEvent(ChatEvent):
    """Event indicating the end of tool use."""

    tool_use_id: str = Field(..., description="ID of the tool use")
    status: str = Field(..., description="Status of tool execution")

    def to_standard_event(self) -> StandardEvent:
        return StandardEvent(
            event_type=StandardEventType.TOOL_END,
            content={"message_id": self.message_id, "tool_use_id": self.tool_use_id, "status": self.status},
        )
