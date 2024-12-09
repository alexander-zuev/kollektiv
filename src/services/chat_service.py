# Chat service is responsible for handling chat requests and responses.abs

from collections.abc import AsyncGenerator
from uuid import UUID

from src.api.v0.schemas.chat_schemas import (
    ChatEvent,
    ChatRequest,
    ConversationListResponse,
    ConversationMessages,
    MessageType,
)
from src.core.chat.claude_assistant import ClaudeAssistant
from src.infrastructure.common.logger import get_logger
from src.models.llm_model import StandardEvent, StandardEventType
from src.services.data_service import DataService

logger = get_logger()


class ConversationMemory:
    """Conversation memory is responsible for storing and managing in memory conversation state."""

    def __init__(self):
        self.conversations = {}

    def add_pending_message(self):
        """Add message to pending state"""
        pass

    def commit_pending(self):
        """Commit pending messages to stable conversation history"""
        pass

    def rollback_pending(self):
        """Discard pending messages from memory"""
        pass


class ChatService:
    """Chat service responsible for handling chat requests and responses, message persistence and history."""

    def __init__(self, claude_assistant: ClaudeAssistant, data_service: DataService):
        self.claude_assistant = claude_assistant
        self.data_service = data_service

    async def stream_response(self, request: ChatRequest) -> AsyncGenerator[ChatEvent, None]:
        """Stream response events back to the client."""
        try:
            async for event in self.claude_assistant.stream_response(request.message):
                match event.event_type:
                    case StandardEventType.TEXT_TOKEN:
                        yield ChatEvent(event_type=MessageType.TOKEN, content=event.content)
                    case StandardEventType.TOOL_START:
                        yield ChatEvent(event_type=MessageType.TOOL_USE, content=event.tool_info)
                    case StandardEventType.TOOL_RESULT:
                        yield ChatEvent(event_type=MessageType.TOOL_RESULT, content=event.content)
                    case StandardEventType.MESSAGE_STOP:
                        yield ChatEvent(event_type=MessageType.DONE, content="")
                    case StandardEventType.ERROR:
                        yield ChatEvent(event_type=MessageType.ERROR, content=event.content)
        except Exception as e:
            logger.error(f"Unexpected error in stream response: {str(e)}", exc_info=True)
            yield ChatEvent(event_type=MessageType.ERROR, content=str(e))

    async def list_conversations(self) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        pass

    async def get_conversation(self, conversation_id: UUID) -> ConversationMessages:
        """Return all messages in a conversation."""
        pass
