from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar, Literal
from uuid import UUID, uuid4

from anthropic.types import MessageParam
from pydantic import BaseModel, Field, model_validator

from src.infra.logger import get_logger
from src.models.base_models import SupabaseModel

logger = get_logger()


# BASIC ANTHROPIC CONTENT MODELS


class ContentBlockType(str, Enum):
    """Types of content blocks in a conversation that are used by Anthropic."""

    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    DOCUMENT = "document"


class ContentBlock(BaseModel):
    """Base content block model"""

    type: str = Field(..., description="Type of the content block")
    index: int | None = Field(None, description="Index of the content block during streaming. None if not streaming.")


class TextBlock(ContentBlock):
    """Simple text content"""

    type: Literal[ContentBlockType.TEXT] = Field(ContentBlockType.TEXT, description="Type of the content block")
    text: str = Field(..., description="Text content of the block")


class ToolUseBlock(ContentBlock):
    """Tool usage by assistant"""

    type: Literal[ContentBlockType.TOOL_USE] = Field(ContentBlockType.TOOL_USE, description="Type of the content block")
    id: str = Field(..., description="ID of the tool use")
    name: str = Field(..., description="Name of the tool")
    input: dict = Field(..., description="Input to the tool")


class ToolResultBlock(ContentBlock):
    """Tool result from assistant"""

    type: Literal[ContentBlockType.TOOL_RESULT] = Field(
        ContentBlockType.TOOL_RESULT, description="Type of the content block"
    )
    tool_use_id: str = Field(..., description="ID of the tool use")
    content: str = Field(..., description="Result returned from the tool")
    is_error: bool = Field(False, description="Error returned from the tool")


# ANTHROPIC STREAMING EVENTS


class StreamEventType(str, Enum):
    """Anthropic streaming event types"""

    # Events based on Anthropic streaming events
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    ERROR = "error"


class MessageStartEvent(BaseModel):
    """Message start event."""

    type: Literal[StreamEventType.MESSAGE_START] = StreamEventType.MESSAGE_START


class ContentBlockStartEvent(BaseModel):
    """Content block start event."""

    type: Literal[StreamEventType.CONTENT_BLOCK_START] = StreamEventType.CONTENT_BLOCK_START
    index: int = Field(..., description="Index of the content block that started streaming.")
    content_block: ContentBlock = Field(..., description="Content block that started streaming.")


class TextDeltaStream(BaseModel):
    """Text delta event."""

    type: Literal["text_delta"] = "text_delta"
    text: str = Field(..., description="Text delta")


class ToolInputJSONStream(BaseModel):
    """Tool use event."""

    type: Literal["input_json_delta"] = "input_json_delta"
    partial_json: str = Field(..., description="Partial JSON for tool use")


class ContentBlockDeltaEvent(BaseModel):
    """Delta content for a block - can be text or JSON"""

    type: Literal[StreamEventType.CONTENT_BLOCK_DELTA] = StreamEventType.CONTENT_BLOCK_DELTA
    delta: TextDeltaStream | ToolInputJSONStream


class ContentBlockStopEvent(BaseModel):
    """Content block stop event."""

    type: Literal[StreamEventType.CONTENT_BLOCK_STOP] = StreamEventType.CONTENT_BLOCK_STOP
    index: int = Field(..., description="Index of the content block that stopped streaming.")


class MessageStopEvent(BaseModel):
    """Message stop event."""

    type: Literal[StreamEventType.MESSAGE_STOP] = StreamEventType.MESSAGE_STOP


class StreamErrorEvent(BaseModel):
    """Error event."""

    type: Literal[StreamEventType.ERROR] = StreamEventType.ERROR
    error: dict = Field(..., description="Error data")


class MessageDeltaEvent(BaseModel):
    """Represents a message delta event."""

    event_type: Literal[StreamEventType.MESSAGE_DELTA] = StreamEventType.MESSAGE_DELTA
    delta: dict = Field(..., description="Delta of the message")
    usage: dict = Field(..., description="Usage of the message")


class StreamEvent(BaseModel):
    """Events emitted by the LLM assistant, based on Anthropic streaming events. These are not client-facing."""

    event_type: StreamEventType = Field(..., description="Type of the event")
    data: (
        MessageStartEvent
        | ContentBlockStartEvent
        | ContentBlockDeltaEvent
        | ContentBlockStopEvent
        | MessageDeltaEvent
        | MessageStopEvent
        | StreamErrorEvent
    ) = Field(..., description="Text delta or error event")


# FRONTEND FACING EVENTS


class FrontendEventType(str, Enum):
    """Unified, flat frontend event types."""

    # Streaming events
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_STOP = "message_stop"

    # Custom chat events
    MESSAGE_ACCEPTED = "message_accepted"
    TOOL_RESULT_MESSAGE = "tool_result_message"
    ASSISTANT_MESSAGE = "assistant_message"
    ERROR = "message_error"


class FrontendChatEvent(BaseModel):
    """A unified, flat frontend chat events model. Incorporates both streaming and custom events. Allows for easier handling of events in the frontend."""

    type: FrontendEventType = Field(..., description="Type of the event")

    # Conversation attributes
    conversation_id: UUID | None = Field(None, description="UUID of the conversation")
    conversation_title: str | None = Field(None, description="Title of the conversation")

    # Content block fields
    index: int | None = Field(None, description="Index of the content block")
    content_block: ContentBlock | None = Field(None, description="Content block")

    # Delta content
    text_delta: str | None = Field(None, description="Text delta")
    tool_input_json_delta: str | None = Field(None, description="Tool input JSON delta")

    # Complete message
    message: ConversationMessage | None = Field(None, description="Complete message")

    # Error handling
    error_message: str | None = Field(None, description="Error message")

    @classmethod
    def from_stream_event(cls, event: StreamEvent) -> FrontendChatEvent:
        """Convert internal stream event to frontend event"""
        match event.event_type:
            case StreamEventType.CONTENT_BLOCK_START:
                return cls(
                    type=FrontendEventType.CONTENT_BLOCK_START,
                    index=event.data.index,
                    content_block=event.data.content_block,
                )
            case StreamEventType.CONTENT_BLOCK_DELTA:
                if isinstance(event.data.delta, TextDeltaStream):
                    return cls(type=FrontendEventType.CONTENT_BLOCK_DELTA, text_delta=event.data.delta.text)
                elif isinstance(event.data.delta, ToolInputJSONStream):
                    return cls(
                        type=FrontendEventType.CONTENT_BLOCK_DELTA,
                        tool_input_json_delta=event.data.delta.partial_json,
                    )
                else:
                    raise ValueError(f"Unknown content block delta type: {type(event.data.delta)}")
            case StreamEventType.CONTENT_BLOCK_STOP:
                return cls(type=FrontendEventType.CONTENT_BLOCK_STOP, index=event.data.index)
            case StreamEventType.MESSAGE_STOP:
                return cls(type=FrontendEventType.MESSAGE_STOP)
            case StreamEventType.ERROR:
                return cls(type=FrontendEventType.ERROR, error_message=str(event.data.error))
            case _:
                raise ValueError(f"Unknown stream event type: {event.event_type}")

    @classmethod
    def create_tool_result_message(cls, tool_result: ToolResultBlock, conversation_id: UUID) -> FrontendChatEvent:
        """Create a ToolResultMessage with the tool result block"""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=Role.USER,
            content=[tool_result],
        )
        return cls(type=FrontendEventType.TOOL_RESULT_MESSAGE, message=message)

    @classmethod
    def create_assistant_message(cls, content_blocks: list[ContentBlock], conversation_id: UUID) -> FrontendChatEvent:
        """Create an AssistantMessage with the assistant message"""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=content_blocks,
        )
        return cls(type=FrontendEventType.ASSISTANT_MESSAGE, message=message)

    @classmethod
    def create_message_accepted_event(cls, conversation_id: UUID, title: str) -> FrontendChatEvent:
        """Create a MessageAcceptedEvent"""
        return cls(
            type=FrontendEventType.MESSAGE_ACCEPTED,
            conversation_id=conversation_id,
            conversation_title=title,
        )

    @classmethod
    def create_error_event(cls, error_message: str) -> FrontendChatEvent:
        """Create an ErrorEvent"""
        return cls(type=FrontendEventType.ERROR, error_message=error_message)


# CONVERSATION AND MESSAGE DOMAIN MODELS


class Role(str, Enum):
    """Roles in the conversation."""

    ASSISTANT = "assistant"
    USER = "user"


class ConversationMessage(SupabaseModel):
    """A message in a conversation between a user and an LLM."""

    message_id: UUID = Field(
        default_factory=uuid4,
        description="UUID of a message. Generated by backend for assistant messages, sent by client for user messages.",
    )
    conversation_id: UUID = Field(..., description="FK reference to a conversation.")
    role: Role = Field(..., description="Role of the message sender")
    content: list[TextBlock | ToolUseBlock | ToolResultBlock] = Field(
        ...,
        description="Content of the message corresponding to Anthropic API",
    )

    _db_config: ClassVar[dict] = {"schema": "chat", "table": "messages", "primary_key": "message_id"}

    @model_validator(mode="before")
    def validate_content(cls, values: dict) -> dict:
        """Ensure the correct model is instantiated for each item in the `content` list."""
        content_data = values.get("content", [])
        resolved_content: list[ContentBlock] = []

        for item in content_data:
            # Inspect the `block_type` field to determine which model to use
            if isinstance(item, TextBlock):
                resolved_content.append(item)
            elif isinstance(item, ToolUseBlock):
                resolved_content.append(item)
            elif isinstance(item, ToolResultBlock):
                resolved_content.append(item)
            elif isinstance(item, dict):
                if item.get("type") == ContentBlockType.TEXT:
                    resolved_content.append(TextBlock(**item))
                elif item.get("type") == ContentBlockType.TOOL_USE:
                    resolved_content.append(ToolUseBlock(**item))
                elif item.get("type") == ContentBlockType.TOOL_RESULT:
                    resolved_content.append(ToolResultBlock(**item))
                else:
                    raise ValueError(f"Unknown content block type: {item.get('type')}, {item}")
            else:
                raise ValueError(f"Unknown content block type: {type(item)}, {item}")

        values["content"] = resolved_content
        return values

    def to_anthropic(self) -> MessageParam:
        """Convert to Anthropic API format"""
        return {
            "role": self.role.value,
            "content": [block.model_dump(exclude={"index"}) for block in self.content],
        }


class Conversation(SupabaseModel):
    """Domain model for a conversation in chat.."""

    conversation_id: UUID = Field(default_factory=uuid4, description="UUID of the conversation")
    user_id: UUID = Field(..., description="FK reference to UUID of the user")
    title: str = Field(default="New Conversation", description="Title of the conversation")
    message_ids: list[UUID] | list = Field(
        default_factory=list, description="FK references to UUIDs of the messages in the conversation"
    )
    token_count: int = Field(default=0, description="Total token count for the conversation, initially 0")
    data_sources: list[UUID] = Field(
        default_factory=list,
        description="FK references to UUIDs of the data sources last active for the conversation",
    )

    _db_config: ClassVar[dict] = {"schema": "chat", "table": "conversations", "primary_key": "conversation_id"}


class ConversationHistory(BaseModel):
    """A list of messages for a conversation"""

    user_id: UUID = Field(
        ...,
        description="Mandatory FK reference to UUID of the user. Kept for easier access to user data and to eliminate the need to query for user id.",
    )
    conversation_id: UUID = Field(..., description="FK reference to UUID of the conversation")
    messages: list[ConversationMessage] = Field(
        default_factory=list, description="List of messages in the conversation"
    )
    token_count: int = Field(default=0, description="Total token count for the conversation, initially 0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last updated timestamp")

    def to_anthropic_messages(self) -> Iterable[MessageParam]:
        """Convert entire history to Anthropic format"""
        result = [msg.to_anthropic() for msg in self.messages]
        return result

    @model_validator(mode="after")
    def validate_messages(self) -> ConversationHistory:
        """Validate message order and roles"""
        for i, msg in enumerate(self.messages[1:], 1):
            prev_msg = self.messages[i - 1]
            if msg.role == prev_msg.role:
                logger.error(f"Consecutive messages cannot have the same role: {msg.role} and {prev_msg.role}")
                raise ValueError("Consecutive messages cannot have the same role")
        return self


class ConversationSummary(BaseModel):
    """Summary of a conversation returned by GET /conversations"""

    conversation_id: UUID = Field(..., description="UUID of the conversation")
    title: str = Field(..., description="Title of the conversation")
    updated_at: datetime = Field(..., description="Last updated timestamp")


# API MODELS
# POST /chat models
class UserMessage(BaseModel):
    """/Chat request model."""

    user_id: UUID = Field(..., description="UUID of the user provided by Supabase")
    message_id: UUID = Field(..., description="UUID of the user message generated by frontend")
    conversation_id: UUID = Field(..., description="UUID of the conversation, generated by FE for new conversations")
    role: Role = Field(Role.USER, description="Role of tc message sender")
    content: list[TextBlock | ToolResultBlock] = Field(..., description="Content of the message")


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
    user_id: UUID = Field(..., description="UUID of the user")
    messages: list[ConversationMessage] = Field(
        default_factory=list, description="List of messages in the conversation"
    )
    updated_at: datetime = Field(..., description="Last updated timestamp")

    @classmethod
    def from_history(cls, history: ConversationHistory) -> ConversationHistoryResponse:
        """Convert a ConversationHistory to a ConversationHistoryResponse"""
        return cls(
            conversation_id=history.conversation_id,
            user_id=history.user_id,
            messages=history.messages,
            updated_at=history.updated_at,
        )
