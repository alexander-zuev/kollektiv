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
from src.core.chat.exceptions import ClientDisconnectError, StreamingError, TokenLimitError
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

            # Get stream from Claude and process events
            async for event in await self.claude_assistant.stream_response(conversation_with_pending):
                try:
                    if event.event_type == StandardEventType.MESSAGE_START:
                        yield LLMResponse(
                            message_type=MessageType.MESSAGE_START, text="", conversation_id=conversation_id
                        )

                    elif event.event_type == StandardEventType.TEXT_TOKEN:
                        yield LLMResponse(
                            message_type=MessageType.TEXT_TOKEN, text=event.content, conversation_id=conversation_id
                        )

                    elif event.event_type == StandardEventType.TOOL_START:
                        # Add tool use to pending messages
                        await self.conversation_manager.add_pending_message(
                            conversation_id=conversation_id, role=Role.ASSISTANT, content=event.content
                        )
                        yield LLMResponse(
                            message_type=MessageType.TOOL_START, text=event.content, conversation_id=conversation_id
                        )

                    elif event.event_type == StandardEventType.TOOL_END:
                        yield LLMResponse(
                            message_type=MessageType.TOOL_END, text=event.content, conversation_id=conversation_id
                        )

                    elif event.event_type == StandardEventType.MESSAGE_STOP:
                        yield LLMResponse(
                            message_type=MessageType.MESSAGE_STOP, text="", conversation_id=conversation_id
                        )
                        # Commit pending messages and save conversation after yielding the stop event
                        await self.conversation_manager.commit_pending(conversation_id)
                        await self.data_service.save_conversation(conversation_id)

                except Exception as e:
                    logger.error(f"Error processing event {event.event_type}: {str(e)}", exc_info=True)
                    # Only yield error for non-cleanup operations
                    if event.event_type != StandardEventType.MESSAGE_STOP:
                        # Re-raise specific error types
                        if isinstance(e, TokenLimitError | StreamingError | ClientDisconnectError):
                            raise
                        # Convert other errors to StreamingError
                        raise StreamingError(f"Error processing event {event.event_type}: {str(e)}") from e

        except (TokenLimitError, StreamingError, ClientDisconnectError) as e:
            # Handle streaming setup errors
            if conversation_id:
                await self.conversation_manager.rollback_pending(conversation_id)
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Yield error response
            yield LLMResponse(message_type=MessageType.ERROR, text=str(e), conversation_id=conversation_id)

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
