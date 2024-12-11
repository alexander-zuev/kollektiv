# Chat service is responsible for handling chat requests and responses.abs

from collections.abc import AsyncGenerator
from uuid import UUID

from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    ConversationMessages,
    LLMResponse,
    MessageType,
)
from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.conversation_manager import ConversationManager
from src.infrastructure.common.logger import get_logger
from src.models.chat_models import ConversationHistory, Role, StandardEvent, StandardEventType
from src.services.data_service import DataService

logger = get_logger()


class ChatService:
    """Orchestrates chat operations, managing conversation state and LLM interactions."""

    def __init__(
        self, claude_assistant: ClaudeAssistant, conversation_manager: ConversationManager, data_service: DataService
    ):
        self.claude_assistant = claude_assistant
        self.conversation_manager = conversation_manager
        self.data_service = data_service

    async def get_response(
        self, user_id: UUID, message: str, conversation_id: UUID | None = None
    ) -> AsyncGenerator[LLMResponse, None]:
        """Process a user message and stream responses."""
        if message is None:
            raise ValueError("Message cannot be None")
        if not message:
            raise ValueError("Message cannot be empty")
        try:
            # Prepare conversation for Claude
            conversation_with_pending = await self._prepare_conversation(
                conversation_id=conversation_id, message=message, user_id=user_id
            )

            # Get conversation_id and send it as the first event
            conversation_id = conversation_with_pending.conversation_id
            yield LLMResponse(message_type=MessageType.CONVERSATION_ID, text=str(conversation_id))

            # Stream response from Claude
            async for event in self.claude_assistant.stream_response(conversation_with_pending):
                if event.event_type == StandardEventType.TEXT_TOKEN:
                    yield LLMResponse(message_type=MessageType.TEXT_TOKEN, text=str(event.content))
                elif event.event_type == StandardEventType.TOOL_START:
                    yield LLMResponse(message_type=MessageType.TOOL_USE, text=str(event.content))
                elif event.event_type == StandardEventType.TOOL_RESULT:
                    # Add tool result to conversation
                    await self.conversation_manager.add_message(
                        conversation_id=conversation_id,
                        role=Role.USER,
                        content=event.content,
                    )
                elif event.event_type == StandardEventType.FULL_MESSAGE:
                    # Add final message to conversation
                    await self.conversation_manager.add_message(
                        conversation_id=conversation_id,
                        role=Role.ASSISTANT,
                        content=event.content,
                    )
                    yield LLMResponse(message_type=MessageType.DONE, text=str(event.content))

            # Once all is done, commit pending messages
            await self.conversation_manager.commit_pending(conversation_id)

        except (RetryableLLMError, NonRetryableLLMError) as e:
            # On error, rollback pending messages if we have a conversation_id
            if 'conversation_id' in locals():
                await self.conversation_manager.rollback_pending(conversation_id)
            yield LLMResponse(message_type=MessageType.ERROR, text=str(e))

    async def _prepare_conversation(
        self, conversation_id: UUID | None, message: str, user_id: UUID
    ) -> ConversationHistory:
        """Prepare a conversation for processing."""
        # Get or create conversation
        if conversation_id is None:
            conversation = await self.conversation_manager.get_or_create_conversation(
                user_id=user_id,
                title="Test Conversation",
                data_sources=[],
            )
            conversation_id = conversation.conversation_id
        else:
            conversation = await self.conversation_manager.get_conversation_with_pending(conversation_id)

        # Add user message to pending state
        await self.conversation_manager.add_pending_message(
            conversation_id=conversation_id,
            role=Role.USER,
            content=message,
        )

        # Get conversation with pending messages
        return await self.conversation_manager.get_conversation_with_pending(conversation_id)

    async def list_conversations(self) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        raise NotImplementedError()

    async def get_conversation(self, conversation_id: UUID) -> ConversationMessages:
        """Return all messages in a conversation."""
        raise NotImplementedError()
