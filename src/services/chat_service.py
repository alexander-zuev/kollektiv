# Chat service is responsible for handling chat requests and responses.abs

from collections.abc import AsyncGenerator
from uuid import UUID

from src.api.v0.schemas.chat_schemas import (
    AssistantResponseEvent,
    ChatResponse,
    ConversationListResponse,
    MessageAcceptedEvent,
    MessageDeltaEvent,
    MessageDoneEvent,
    UserMessage,
)
from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.infrastructure.common.logger import get_logger
from src.models.chat_models import (
    Conversation,
    ConversationMessage,
    Role,
    StreamingEventType,
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

    async def get_response(self, user_message: UserMessage) -> AsyncGenerator[ChatResponse, None]:
        """Process a user message and stream responses."""
        try:
            # 1. Prepare conversation
            if user_message.conversation_id:
                # If it's an existing conversation
                conversation_id = user_message.conversation_id
                logger.info(f"Continuing conversation: {conversation_id}")
                conversation = await self.conversation_manager.get_conversation(
                    conversation_id=conversation_id, message=user_message
                )
            else:
                # 1. Create a conversation if it doesn't exist
                conversation = await self.conversation_manager.create_conversation(message=user_message)
                user_message.conversation_id = conversation.conversation_id
                logger.info(f"Created new conversation: {conversation.conversation_id}")

            # 2. Send conversation_id to the client
            yield ChatResponse(event=MessageAcceptedEvent(conversation_id=conversation.conversation_id))
            logger.debug(f"Sent MessageAcceptedEvent for conversation: {conversation.conversation_id}")

            # 3. Add user message to pending messages
            await self.conversation_manager.add_pending_message(message=user_message)

            # 3. Send user message to LLM and start streaming response
            async for event in self.claude_assistant.stream_response(conv_history=conversation):
                match event.event_type:
                    # tokens -> stream to user
                    case StreamingEventType.TEXT_TOKEN:
                        yield ChatResponse(event=MessageDeltaEvent(text_delta=event.event_data.text))
                    case StreamingEventType.MESSAGE_STOP:
                        logger.debug("Message stream completed")
                    case StreamingEventType.ASSISTANT_MESSAGE:
                        logger.info(f"Processing assistant message for conversation: {conversation.conversation_id}")
                        assistant_message = ConversationMessage(
                            conversation_id=conversation.conversation_id,
                            role=Role.ASSISTANT,
                            content=event.event_data.content,
                        )
                        # Add to pending messages
                        await self.conversation_manager.add_pending_message(message=assistant_message)

                        # Yield the full message text
                        yield ChatResponse(event=AssistantResponseEvent(response=assistant_message))

                        # If tool use in assisntant response
                        # add tool_result to pending as a user message
                        # get assistnat response to tool result
                        # yield assistnat response again to the user

            # 5. Commit pending messages
            logger.info(f"Committing conversation updates for: {conversation.conversation_id}")
            await self.conversation_manager.commit_pending(conversation_id=conversation.conversation_id)

            # 6. Done
            yield ChatResponse(event=MessageDoneEvent())
            logger.info(f"Completed message processing for conversation: {conversation.conversation_id}")

        except RetryableLLMError as e:
            logger.error(f"Retryable error in conversation {user_message.conversation_id}: {str(e)}", exc_info=True)
            raise RetryableLLMError(
                original_error=e,
                message=f"Error in chat service processing message: {str(e)} for user {user_message.user_id}",
            ) from e
        except NonRetryableLLMError as e:
            logger.error(f"Non-retryable error in conversation {user_message.conversation_id}: {str(e)}", exc_info=True)
            raise NonRetryableLLMError(
                original_error=e,
                message=f"Error in chat service processing message: {str(e)} for user {user_message.user_id}",
            ) from e

    async def get_conversations(self, user_id: UUID) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        conversations = await self.data_service.get_conversations(user_id)
        return conversations

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Return a single conversation by its ID in accordance with RLS policies."""
        conversation = await self.data_service.get_conversation(conversation_id)
        return conversation
