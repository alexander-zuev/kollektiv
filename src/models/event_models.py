from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StandardEventType(str, Enum):
    """Standardized event types mapped from Anthropic events."""

    # Regular message events
    MESSAGE_START = "message_start"
    MESSAGE_TOKEN = "message_token"  # maps from text event
    MESSAGE_END = "message_end"  # maps from message_stop

    # Tool-related events
    TOOL_START = "tool_start"  # maps from content_block_start with tool_use
    TOOL_END = "tool_end"  # maps from content_block_stop with tool_use
    TOOL_RESULT = "tool_result"  # when tool execution completes

    # Error events
    ERROR = "error"  # any error during processing


class StandardEvent(BaseModel):
    """Standard event structure for internal use."""

    event_type: StandardEventType
    content: str | dict[str, Any] = Field(description="Event content - text for tokens, structured data for tools")
    tool_info: dict[str, Any] | None = Field(None, description="Tool-specific information when relevant")
    message_id: UUID | None = Field(None, description="ID of the message this event belongs to")
