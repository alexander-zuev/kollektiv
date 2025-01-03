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
from src.infra.logger import get_logger
from src.models.chat_models import (
    Conversation,
    ConversationHistory,
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
                conversation = await self.conversation_manager.get_conversation_history(
                    conversation_id=conversation_id, message=user_message
                )
                logger.debug(f"Retrieved conversation with ID: {conversation.conversation_id}")
            else:
                logger.info(f"Creating new conversation for user {user_message.user_id}")
                conversation = await self.conversation_manager.create_conversation(message=user_message)
                user_message.conversation_id = conversation.conversation_id
                logger.debug(f"Created conversation with ID: {conversation.conversation_id}")

            # 2. Send conversation_id to client
            yield ChatResponse(event=MessageAcceptedEvent(conversation_id=conversation.conversation_id))
            logger.debug(f"Sent MessageAcceptedEvent for conversation: {conversation.conversation_id}")

            # 3. Add user message to pending
            await self.conversation_manager.add_pending_message(message=user_message)
            logger.debug(
                f"Added user message to pending for conversation {conversation.conversation_id}: "
                f"{user_message.content[:100]}..."
            )

            # 4. Process stream
            async for event in self._process_stream(conversation):
                yield event

            logger.info(f"Completed message processing for conversation {conversation.conversation_id}")

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

    async def _process_stream(
        self, conversation: ConversationHistory, tool_use_count: int = 0
    ) -> AsyncGenerator[ChatResponse, None]:
        """Process a stream of events and yield ChatResponse objects."""
        max_tool_retries_per_turn = 2
        tool_result_processed = False

        logger.debug(
            f"Starting stream processing for conversation {conversation.conversation_id} "
            f"(tool use count: {tool_use_count})"
        )

        async for event in self.claude_assistant.stream_response(conv_history=conversation):
            match event.event_type:
                case StreamingEventType.TEXT_TOKEN:
                    yield ChatResponse(event=MessageDeltaEvent(text_delta=event.event_data.text))

                case StreamingEventType.ASSISTANT_MESSAGE:
                    logger.info(f"Processing assistant message for conversation {conversation.conversation_id}")
                    assistant_message = ConversationMessage(
                        conversation_id=conversation.conversation_id,
                        role=Role.ASSISTANT,
                        content=event.event_data.content,
                    )
                    await self.conversation_manager.add_pending_message(message=assistant_message)
                    logger.debug(f"Added assistant message to pending for conversation {conversation.conversation_id}")
                    yield ChatResponse(event=AssistantResponseEvent(response=assistant_message))
                    logger.debug(f"ASSISTANT RESPONSE FOR DEBUGGING AFTER ADDING TO PENDING: {assistant_message}")

                case StreamingEventType.TOOL_RESULT:
                    if tool_use_count >= max_tool_retries_per_turn:
                        logger.warning(
                            f"Max tool retries ({max_tool_retries_per_turn}) reached for conversation "
                            f"{conversation.conversation_id}"
                        )
                        continue

                    logger.info(
                        f"Processing tool result for conversation {conversation.conversation_id} "
                        f"(attempt {tool_use_count + 1}/{max_tool_retries_per_turn})"
                    )
                    tool_result = event.event_data.content
                    tool_result_message = ConversationMessage(
                        conversation_id=conversation.conversation_id,
                        role=Role.USER,
                        content=[tool_result],
                    )

                    await self.conversation_manager.add_pending_message(message=tool_result_message)
                    logger.debug(f"Added tool result to pending for conversation {tool_result_message}")

                    await self.conversation_manager.commit_pending(conversation_id=conversation.conversation_id)
                    logger.debug(f"Committed pending messages for conversation {conversation.conversation_id}")

                    tool_result_processed = True
                    conversation = await self.conversation_manager.get_conversation_history(
                        conversation_id=conversation.conversation_id,
                    )
                    logger.debug(
                        f"Retrieved updated conversation history for {conversation.conversation_id}. "
                        f"Starting new stream..."
                    )

                    async for new_event in self._process_stream(conversation, tool_use_count + 1):
                        yield new_event

                case StreamingEventType.MESSAGE_STOP:
                    if not tool_result_processed:
                        logger.debug(
                            f"No tool result processed, committing pending messages for conversation "
                            f"{conversation.conversation_id}"
                        )
                        await self.conversation_manager.commit_pending(conversation_id=conversation.conversation_id)
                    else:
                        logger.debug(
                            f"Tool result already processed for conversation {conversation.conversation_id}, "
                            f"skipping commit"
                        )
                    yield ChatResponse(event=MessageDoneEvent())
                    return

    async def get_conversations(self, user_id: UUID) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        conversations = await self.data_service.get_conversations(user_id)
        return conversations

    # TODO: this should load in the sources for the conversation
    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Return a single conversation by its ID in accordance with RLS policies."""
        conversation = await self.data_service.get_conversation(conversation_id)

        # Load data source summaries by id
        # Update system prompt with data source summaries

        return conversation

    # TODO: which endpoint and method should handle the update of the data sources linked to a conversation?
