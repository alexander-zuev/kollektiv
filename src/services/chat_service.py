# Chat service is responsible for handling chat requests and responses.abs

from collections.abc import AsyncGenerator
from uuid import UUID

from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    ConversationMessages,
    LLMResponse,
    MessageType,
)
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.conversation_manager import ConversationManager
from src.infrastructure.common.logger import get_logger
from src.models.chat_models import ConversationHistory, Role, StandardEventType
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
        try:
            # Prepare conversation for Claude
            conversation_with_pending = await self._prepare_conversation(
                conversation_id=conversation_id, message=message
            )

            # Send to Claude and stream the response
            async for event in self.claude_assistant.stream_response(conversation_with_pending):
                if event.event_type == StandardEventType.TOOL_START:
                    # Add tool use to pending messages
                    await self.conversation_manager.add_pending_message(
                        conversation_id=conversation_id, role=Role.ASSISTANT, text=event.content
                    )
                    yield LLMResponse(message_type=MessageType.TOOL_USE, text=event.content)

                elif event.event_type == StandardEventType.MESSAGE_STOP:
                    # 5. On successful completion:
                    # - Commit pending to stable conversation
                    # - Save to DB
                    # await self.conversation_manager.commit_pending(conversation_id)
                    # await self.data_service.save_conversation(conversation)
                    yield LLMResponse(message_type=MessageType.DONE, text="")

                else:
                    yield LLMResponse(message_type=MessageType.TEXT_TOKEN, text=event.content)

        except Exception as e:
            # On error, rollback pending messages
            await self.conversation_manager.rollback_pending(conversation_id)
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            yield LLMResponse(message_type=MessageType.ERROR, text=str(e))

    async def _prepare_conversation(self, conversation_id: UUID | None, message: str) -> ConversationHistory:
        # 1. Get or create empty stable conversation
        conversation = await self.conversation_manager.get_or_create_conversation(conversation_id)

        # 2. Add user message to pending state
        conversation_id = conversation.conversation_id
        await self.conversation_manager.add_pending_message(
            conversation_id=conversation_id, role=Role.USER, content=message
        )

        # 3. Combine stable + pending messages for Claude
        conversation_with_pending = await self.conversation_manager.get_conversation_with_pending(conversation_id)
        return conversation_with_pending

    async def list_conversations(self) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        pass

    async def get_conversation(self, conversation_id: UUID) -> ConversationMessages:
        """Return all messages in a conversation."""
        pass
