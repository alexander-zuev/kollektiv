# Chat service is responsible for handling chat requests and responses.abs

import json
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.llm_assistant import ClaudeAssistant
from src.infra.logger import get_logger
from src.models.chat_models import (
    ContentBlock,
    ConversationHistory,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationMessage,
    FrontendChatEvent,
    Role,
    StreamEvent,
    StreamEventType,
    TextBlock,
    TextDeltaStream,
    ToolInputJSONStream,
    ToolUseBlock,
    UserMessage,
)
from src.services.data_service import DataService

logger = get_logger()


class StreamState:
    """State of the stream, including the current content block and the list of content blocks."""

    def __init__(self, conversation_id: UUID, user_id: UUID):
        self.conversation_id: UUID = conversation_id
        self.user_id: UUID = user_id
        self.current_blocks: list[ContentBlock] = []
        self.current_block: ContentBlock | None = None
        self.has_tool_use = False  # Track if we've seen a tool use block
        self.tool_input: str = ""

    def handle_block_start(self, block: ContentBlock) -> None:
        """Start new content block"""
        self.current_block = block
        if isinstance(block, ToolUseBlock):
            self.has_tool_use = True
            self.tool_input = ""

    def handle_delta(self, delta: TextDeltaStream | ToolInputJSONStream) -> None:
        """Accumulate delta into current block"""
        if self.current_block is None:
            raise ValueError("No current block to accumulate delta into")

        if isinstance(delta, TextDeltaStream):
            if not isinstance(self.current_block, TextBlock):
                raise ValueError("Text delta for non-text block")
            self.current_block.text += delta.text

        elif isinstance(delta, ToolInputJSONStream):
            if not isinstance(self.current_block, ToolUseBlock):
                raise ValueError("Tool input delta for non-tool block")
            else:
                self.tool_input += delta.partial_json

    def handle_block_stop(self) -> None:
        """Finalize current block"""
        if self.current_block:
            if isinstance(self.current_block, ToolUseBlock):
                try:
                    # Parse the accumulated string into a dictionary
                    self.current_block.input = json.loads(self.tool_input)
                    self.tool_input = ""
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse tool input: {self.tool_input}")
                    self.current_block.input = {}  # Set to empty dict on error
            self.current_blocks.append(self.current_block)
            self.current_block = None


class ChatService:
    """
    Orchestrates chat operations, managing conversation state and LLM interactions.

    Stream Flow:
    1. User message received -> get_response()
    2. Setup conversation history
    3. Start stream processing
    4. Transform Anthropic events to frontend events
    5. Handle tool use if needed
    6. Complete conversation turn

    Error Handling:
    - RetryableLLMError: Temporary failures that can be retried
    - NonRetryableLLMError: Permanent failures requiring user intervention
    """

    # TODO: clear pending on errirs

    def __init__(
        self, claude_assistant: ClaudeAssistant, conversation_manager: ConversationManager, data_service: DataService
    ):
        self.claude_assistant = claude_assistant
        self.conversation_manager = conversation_manager
        self.data_service = data_service

    def get_message_accepted_event(self, conversation_id: UUID) -> FrontendChatEvent:
        """Returns a MessageAcceptedEvent to the client"""
        event = FrontendChatEvent.create_message_accepted_event(
            conversation_id=conversation_id,
            title="New conversation",
        )
        logger.debug(f"Sent MessageAcceptedEvent for conversation: {conversation_id}")
        return event

    async def get_response(self, user_message: UserMessage) -> AsyncGenerator[FrontendChatEvent, None]:
        """Process a user message and stream responses."""
        try:
            logger.info(f"Getting response for user message: {user_message}")

            # Prepare conversation history
            history = await self.conversation_manager.setup_new_conv_history_turn(user_message)
            yield self.get_message_accepted_event(history.conversation_id)

            # Setup stream
            async for frontend_event in self.process_stream(history):
                yield frontend_event

            # Handle conversation turn
            await self.handle_conversation_turn(history)

            logger.debug(f"Conversation turn handled for conversation: {history.conversation_id}")

        except RetryableLLMError as e:
            logger.error(f"Retryable error in conversation {user_message.conversation_id}: {str(e)}", exc_info=True)
            yield FrontendChatEvent.create_error_event(
                error_message=f"Error in chat service processing message: {str(e)} for user {user_message.user_id}",
            )
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

    def handle_content_block_start(self, event: StreamEvent) -> FrontendChatEvent:
        """Yields a FrontendEvent with the content block which has just started"""
        if isinstance(event.data.content_block, TextBlock):
            return FrontendChatEvent.from_stream_event(event)
        elif isinstance(event.data.content_block, ToolUseBlock):
            return FrontendChatEvent.from_stream_event(event)
        else:
            raise ValueError(f"Unknown content block type: {type(event.data.content_block)}")

    def handle_content_block_delta(self, event: StreamEvent) -> FrontendChatEvent:
        """Emits a FrontendEvent with the delta"""
        if isinstance(event.data.delta, TextDeltaStream):
            return FrontendChatEvent.from_stream_event(event)
        elif isinstance(event.data.delta, ToolInputJSONStream):
            return FrontendChatEvent.from_stream_event(event)
        else:
            raise ValueError(f"Unknown content block delta type: {type(event.data)}")

    def handle_content_block_stop(self, event: StreamEvent) -> FrontendChatEvent:
        """Content Block stop event"""
        return FrontendChatEvent.from_stream_event(event)

    def handle_message_stop(self, event: StreamEvent) -> FrontendChatEvent:
        """Emits message stop event."""
        #
        return FrontendChatEvent.from_stream_event(event)

    def handle_stream_error(self, event: StreamEvent) -> FrontendChatEvent:
        """Emits error event."""
        logger.warning(f"LLM error: {event.data.error}")
        return FrontendChatEvent.from_stream_event(event)

    async def handle_assistant_message(
        self, conversation_history: ConversationHistory, state: StreamState
    ) -> ConversationMessage:
        """Emits assistant message event."""
        # Emit assistant message
        assistant_message = ConversationMessage(
            conversation_id=conversation_history.conversation_id,
            role=Role.ASSISTANT,
            content=state.current_blocks,
        )

        await self.conversation_manager.add_pending_message(message=assistant_message)

        return assistant_message

    def handle_assistant_message_event(self, assistant_message: ConversationMessage) -> FrontendChatEvent:
        """Emits assistant message event."""
        return FrontendChatEvent.create_assistant_message(
            content_blocks=assistant_message.content, conversation_id=assistant_message.conversation_id
        )

    async def handle_conversation_turn(self, conversation_history: ConversationHistory) -> None:
        """Handles update of the conversation history post-turn"""
        await self.conversation_manager.commit_pending(conversation_id=conversation_history.conversation_id)

    async def process_stream(
        self, conversation_history: ConversationHistory
    ) -> AsyncGenerator[FrontendChatEvent, None]:
        """Process a stream of events and yield Client (FE) chat events"""
        logger.debug(f"Starting stream processing for conversation {conversation_history.conversation_id}")

        state = StreamState(conversation_id=conversation_history.conversation_id, user_id=conversation_history.user_id)

        try:
            async for event in self.claude_assistant.stream_response(conv_history=conversation_history):
                match event.event_type:
                    case StreamEventType.MESSAGE_START:
                        continue  # not used right now
                    case StreamEventType.CONTENT_BLOCK_START:
                        # Emit event
                        yield self.handle_content_block_start(event)

                        # Update state
                        state.handle_block_start(event.data.content_block)
                    case StreamEventType.CONTENT_BLOCK_DELTA:
                        # Emit event
                        yield self.handle_content_block_delta(event)

                        # Update state
                        state.handle_delta(event.data.delta)
                    case StreamEventType.CONTENT_BLOCK_STOP:
                        # Emit event
                        yield self.handle_content_block_stop(event)

                        # Update state
                        state.handle_block_stop()
                    case StreamEventType.MESSAGE_DELTA:
                        continue  # not used right now, but could be to update token count (later)
                    case StreamEventType.MESSAGE_STOP:
                        # Emit message stop event
                        yield self.handle_message_stop(event)

                        # Emit assistant message
                        message = await self.handle_assistant_message(conversation_history, state)
                        yield self.handle_assistant_message_event(message)
                    case StreamEventType.ERROR:
                        yield self.handle_stream_error(event)
                        await self.conversation_manager.clear_pending(
                            conversation_id=conversation_history.conversation_id
                        )
                        raise NonRetryableLLMError(
                            original_error=event.data.error,
                            message=f"Stream processing failed: {str(event.data.error)}",
                        )

            if state.has_tool_use:
                async for tool_event in self.handle_tool_use(state):
                    yield tool_event
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            await self.conversation_manager.clear_pending(conversation_id=conversation_history.conversation_id)
            raise NonRetryableLLMError(original_error=e, message=f"Stream processing failed: {str(e)}") from e

    async def handle_tool_use(self, state: StreamState) -> AsyncGenerator[FrontendChatEvent, None]:
        """Handles tool use"""
        # Add error handling
        try:
            # Get tool result
            for block in state.current_blocks:
                if isinstance(block, ToolUseBlock):
                    tool_use_block = block
                    break

            tool_result = await self.claude_assistant.get_tool_result(tool_use_block, state.user_id)

            # Create user message
            user_message = UserMessage(
                conversation_id=state.conversation_id,
                message_id=uuid4(),
                user_id=state.user_id,
                role=Role.USER,
                content=[tool_result],
            )

            # Launch new stream
            async for event in self.get_response(user_message):
                yield event
        except Exception as e:
            logger.error(f"Error handling tool use: {str(e)}", exc_info=True)
            yield FrontendChatEvent.create_error_event(f"Error handling tool use: {str(e)}")

    async def get_conversations(self, user_id: UUID) -> ConversationListResponse:
        """Return a list of all conversations for a users, ordered into time groups."""
        conversations = await self.data_service.get_conversations(user_id)
        return conversations

    # TODO: this should load in the sources for the conversation
    async def get_conversation(self, conversation_id: UUID) -> ConversationHistoryResponse:
        """Return a single conversation by its ID in accordance with RLS policies."""
        # Get conversation history (RLS will ensure user can only access their conversations)
        history = await self.conversation_manager.get_conversation_history(conversation_id)
        if history is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Convert to response
        return ConversationHistoryResponse(conversation_id=history.conversation_id, messages=history.messages)

    # TODO: which endpoint and method should handle the update of the data sources linked to a conversation?
