# Chat service is responsible for handling chat requests and responses.abs

from collections.abc import AsyncGenerator
from uuid import UUID

from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    LLMResponse,
    MessageType,
)
from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.infrastructure.common.logger import get_logger
from src.models.chat_models import (
    Conversation,
    ConversationHistory,
    Role,
    StandardEvent,
    StandardEventType,
    TextBlock,
)
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

            # Get conversation_id and send it as the first event
            conversation_id = conversation_with_pending.conversation_id
            yield LLMResponse(message_type=MessageType.CONVERSATION_ID, conversation_id=conversation_id)

            # Send to Claude and stream the response
            async for event in self.claude_assistant.stream_response(conversation_with_pending):
                # what do we need to display
                match event.event_type:
                    # tokens -> stream to user
                    case StandardEventType.TEXT_TOKEN:
                        yield LLMResponse(message_type=MessageType.TEXT_TOKEN, text_token=event.content[0].text)
                    # tool use -> just note them for now
                    case StandardEventType.TOOL_START:
                        yield LLMResponse(
                            message_type=MessageType.TOOL_USE,
                            structured_content=[
                                block.model_dump(by_alias=True, exclude_none=True) for block in event.content
                            ],
                        )
                    case StandardEventType.TOOL_RESULT:
                        # add tool result to conversation
                        await self.conversation_manager.add_message_to_conversation(
                            conversation_id=conversation_id, role=Role.USER, content=event.content
                        )
                        logger.debug(f"Added tool result to conversation: {event.content}")
                        yield LLMResponse(
                            message_type=MessageType.TOOL_RESULT,
                            structured_content=[
                                block.model_dump(by_alias=True, exclude_none=True) for block in event.content
                            ],
                        )
                    # message stop -> this is just a signal
                    case StandardEventType.MESSAGE_STOP:
                        logger.debug("Message stop")
                    # final message -> add to conversation
                    case StandardEventType.FULL_MESSAGE:
                        # Add pending assistant message to conversation
                        assistant_message = await self.conversation_manager.add_message_to_pending_conversation(
                            conversation_id=conversation_id,
                            role=Role.ASSISTANT,
                            content=event.content,
                        )

                        # Yield the full message text
                        yield LLMResponse(
                            message_id=assistant_message.message_id,
                            message_type=MessageType.FULL_MESSAGE,
                            structured_content=[
                                block.model_dump(by_alias=True, exclude_none=True) for block in event.content
                            ],
                        )

            # Once all is done and said, commit pending messages
            await self.conversation_manager.commit_pending(conversation_id)

            # Yield DONE event
            yield LLMResponse(message_type=MessageType.DONE, text="===Streaming complete===")
            logger.debug("Message DONE event yielded")

        except RetryableLLMError as e:
            # On error, rollback pending messages
            await self.conversation_manager.rollback_pending(conversation_id)
            # Log the error
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Add context and re-raise
            raise RetryableLLMError(
                original_error=RetryableLLMError,
                message=f"Error in chat service processing message: {str(e)} for user {user_id}",
            ) from e
        except NonRetryableLLMError as e:
            # On error, rollback pending messages
            await self.conversation_manager.rollback_pending(conversation_id)
            # Log the error
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Add context and re-raise
            raise NonRetryableLLMError(
                original_error=NonRetryableLLMError,
                message=f"Error in chat service processing message: {str(e)} for user {user_id}",
            ) from e

    async def _handle_stream_events(self, event: StandardEvent) -> LLMResponse:
        yield LLMResponse(message_type=MessageType.TEXT_TOKEN, text=event.content)

    async def _prepare_conversation(self, conversation_id: UUID | None, message: str) -> ConversationHistory:
        # 1. Get or create empty stable conversation
        conversation = await self.conversation_manager.get_or_create_conversation(conversation_id)

        # 2. Add user message to pending state
        conversation_id = conversation.conversation_id
        await self.conversation_manager.add_message_to_pending_conversation(
            conversation_id=conversation_id, role=Role.USER, content=[TextBlock(text=message)]
        )

        # 3. Combine stable + pending messages for Claude
        conversation_with_pending = await self.conversation_manager.get_conversation_with_pending(conversation_id)
        return conversation_with_pending

    async def get_conversations(self, user_id: UUID) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        conversations = await self.data_service.get_conversations(user_id)
        return conversations

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Return a single conversation by its ID in accordance with RLS policies."""
        conversation = await self.data_service.get_conversation(conversation_id)
        return conversation
