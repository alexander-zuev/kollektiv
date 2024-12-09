from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.chat_models import ConversationMessage

# Chat models


class UserMessage(BaseModel):
    """Chat request model from users. Corresponds to FE model."""

    user_id: UUID = Field(..., description="UUID of the user provided by Supabase")
    message: str = Field(..., description="User message")
    conversation_id: UUID | None = Field(None, description="UUID of the conversation")
    data_sources: list[UUID] = Field(..., description="List of data sources IDs enabaled in this conversation")


class MessageType(str, Enum):
    """Client-facing event types."""

    TEXT_TOKEN = "text_token"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"


class LLMResponse(BaseModel):
    """Client-facing event structure."""

    message_type: MessageType = Field(..., description="Type of the llm message")
    text: str = Field(..., description="Text contetn of the llm message")


# Conversation models
class ConversationSummary(BaseModel):
    """Single conversation summary for the list view."""

    conversation_id: UUID = Field(..., description="UUID of the conversation")
    title: str = Field(..., description="Title of the conversation")
    data_sources: list[UUID] = Field(
        ..., description="FK references to UUIDs of the data sources last active for the conversation"
    )


class TimeGroup(str, Enum):
    """Time periods for conversation grouping."""

    RECENT = "Last 7 days"
    LAST_MONTH = "Last 30 days"
    OLDER = "Older"


class ConversationGroup(BaseModel):
    """Group of conversations by time period."""

    time_group: TimeGroup = Field(..., description="Time period for the conversation group")
    conversations: list[ConversationSummary] = Field(..., description="List of conversations in the group")


class ConversationListResponse(BaseModel):
    """API response for grouped conversations."""

    recent: ConversationGroup = Field(..., description="Group of conversations from the last 7 days")
    last_month: ConversationGroup = Field(..., description="Group of conversations from the last 30 days")
    older: ConversationGroup = Field(..., description="Group of conversations older than 30 days")


class ConversationMessages(BaseModel):
    """API response for all messages in a conversation."""

    messages: list[ConversationMessage] = Field(..., description="List of messages in the conversation")
