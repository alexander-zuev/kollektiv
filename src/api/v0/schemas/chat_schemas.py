from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

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
    CONVERSATION_ID = "conversation_id"
    DONE = "done"
    ERROR = "error"


class LLMResponse(BaseModel):
    """Client-facing event structure."""

    message_type: MessageType = Field(..., description="Type of the llm message")
    text: str | dict = Field(..., description="Text or dictionary of the llm message")


class ConversationSummary(BaseModel):
    """Summary of a conversation returned by GET /conversations"""

    conversation_id: UUID = Field(..., description="UUID of the conversation")
    title: str = Field(..., description="Title of the conversation")
    data_sources: list[UUID] = Field(
        ..., description="FK references to UUIDs of the data sources last active for the conversation"
    )
    updated_at: datetime = Field(..., description="Last updated timestamp")


class ConversationListResponse(BaseModel):
    """Object returned by GET /conversations"""

    conversations: list[ConversationSummary] = Field(..., description="List of conversations")
