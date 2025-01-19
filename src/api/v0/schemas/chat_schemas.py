from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.chat_models import (
    ConversationMessage,
    ConversationSummary,
    Role,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


# POST /chat models
class UserMessage(BaseModel):
    """/Chat request model."""

    user_id: UUID = Field(..., description="UUID of the user provided by Supabase")
    message_id: UUID = Field(..., description="UUID of the user message generated by frontend")
    conversation_id: UUID = Field(..., description="UUID of the conversation, generated by FE for new conversations")
    role: Role = Field(Role.USER, description="Role of tc message sender")
    content: list[TextBlock | ToolUseBlock | ToolResultBlock] = Field(..., description="Content of the message")


class ChatEventType(str, Enum):
    """Client-facing event types."""

    MESSAGE_ACCEPTED = "message_accepted"  # returns conversation_id
    MESSAGE_DELTA = "message_delta"  # returns message_id
    MESSAGE_DONE = "message_done"  # stream is complete
    MESSAGE_ERROR = "message_error"  # error message

    TOOL_USE = "tool_use"  # tool use event
    TOOL_RESULT = "tool_result"  # tool result event
    ASSISTANT_RESPONSE = "assistant_response"  # full content message of the assistant


class MessageAcceptedEvent(BaseModel):
    """Represents a message accepted event."""

    event_type: Literal[ChatEventType.MESSAGE_ACCEPTED] = ChatEventType.MESSAGE_ACCEPTED
    conversation_id: UUID = Field(..., description="UUID of the conversation returned by the server")
    conversation_title: str = Field(..., description="Title of the conversation, determined by the backend.")


class MessageDeltaEvent(BaseModel):
    """Represents a message delta event."""

    event_type: Literal[ChatEventType.MESSAGE_DELTA] = ChatEventType.MESSAGE_DELTA
    text_delta: str = Field(..., description="Delta of the message")


class AssistantResponseEvent(BaseModel):
    """Represents a full assistant response aligned with the domain model."""

    event_type: Literal[ChatEventType.ASSISTANT_RESPONSE] = ChatEventType.ASSISTANT_RESPONSE
    response: ConversationMessage = Field(..., description="Full message response")


class ToolUseEvent(BaseModel):
    """Represents a tool use event."""

    event_type: Literal[ChatEventType.TOOL_USE] = ChatEventType.TOOL_USE
    tool_use: ToolUseBlock = Field(..., description="Tool use block")


class ToolResultEvent(BaseModel):
    """Represents a tool result event."""

    event_type: Literal[ChatEventType.TOOL_RESULT] = ChatEventType.TOOL_RESULT
    tool_result: ToolResultBlock = Field(..., description="Tool result content block")


class MessageDoneEvent(BaseModel):
    """Represents a message done event."""

    event_type: Literal[ChatEventType.MESSAGE_DONE] = ChatEventType.MESSAGE_DONE


class ErrorEvent(BaseModel):
    """Represents an error event."""

    event_type: Literal[ChatEventType.MESSAGE_ERROR] = ChatEventType.MESSAGE_ERROR
    error_message: str = Field(..., description="Error message")


class ChatResponse(BaseModel):
    """/chat response model."""

    event: (
        MessageAcceptedEvent
        | MessageDeltaEvent
        | AssistantResponseEvent
        | ToolUseEvent
        | ToolResultEvent
        | MessageDoneEvent
        | ErrorEvent
    ) = Field(..., description="Event data")


# GET /conversations


class ConversationListResponse(BaseModel):
    """List of conversations returned by GET /conversations."""

    conversations: list[ConversationSummary] = Field(
        default_factory=list, description="List of all user's conversations, empty list if no conversations exist"
    )


# GET /conversations/{conversation_id}
class ConversationHistoryResponse(BaseModel):
    """Object returned by GET /conversations/{conversation_id}."""

    conversation_id: UUID = Field(..., description="UUID of the conversation")
    messages: list[ConversationMessage] = Field(
        default_factory=list, description="List of messages in the conversation"
    )
