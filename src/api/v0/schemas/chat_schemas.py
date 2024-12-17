from datetime import datetime
from enum import Enum
from typing import Any
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

    CONVERSATION_ID = "conversation_id"
    TEXT_TOKEN = "text_token"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"

    DONE = "done"
    FULL_MESSAGE = "full_message"
    ERROR = "error"


class Error(BaseModel):
    """Represents an error event."""

    error_message: str = Field(..., description="Error message")
    error_type: str | None = Field(None, description="Optional error type identifier")


class LLMResponse(BaseModel):
    """Client-facing event structure."""

    message_id: UUID | None = Field(
        None, description="UUID of the message (useful for full assistant message, primarily for internal use)"
    )
    conversation_id: UUID | None = Field(None, description="UUID of the conversation")
    message_type: MessageType = Field(..., description="Type of the llm message")
    text_token: str | None = Field(None, description="Text token from the LLM")
    structured_content: list[dict[str, Any]] | None = Field(None, description="Structured content of the message")
    error: Error | None = Field(None, description="Error information")
    text: str | None = Field(None, description="Full text of the message (for full assistant message)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message_type": MessageType.CONVERSATION_ID,
                    "conversation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                },
                {
                    "message_type": MessageType.TEXT_TOKEN,
                    "text_token": "Hello",
                },
                {
                    "message_type": MessageType.TOOL_USE,
                    "tool_use": {
                        "tool_name": "search",
                        "tool_input": "What is the weather in London?",
                    },
                },
                {
                    "message_type": MessageType.ERROR,
                    "error": {
                        "error_message": "Something went wrong",
                        "error_type": "APIError",
                    },
                },
                {"message_type": MessageType.DONE, "text": "===Streaming complete==="},
                {
                    "message_type": MessageType.FULL_MESSAGE,
                    "message_id": "a1b2c3d4-e5f6-4789-9012-345678901234",
                    "text": "This is the full assistant message.",
                },
            ]
        }
    }


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
