import json
from uuid import UUID

import redis
import tiktoken
from redis.exceptions import RedisError

from src.core._exceptions import KollektivError
from src.infra.data.redis_repository import RedisRepository
from src.infra.logger import get_logger
from src.models.chat_models import (
    Conversation,
    ConversationHistory,
    ConversationMessage,
    Role,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from src.services.data_service import DataService

logger = get_logger()

# TODO: refactor token counting https://github.com/anthropics/anthropic-sdk-python?tab=readme-ov-file#token-counting


class ConversationManager:
    """Manages conversation state, including in-memory storage and token management."""

    def __init__(
        self,
        data_service: DataService,
        redis_repository: RedisRepository,
        max_tokens: int = 200000,
        tokenizer: str = "cl100k_base",
    ):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding(tokenizer)
        # Redis
        self.redis_repository = redis_repository
        # Supabase
        self.data_service = data_service

    async def add_pending_message(self, message: ConversationMessage | UserMessage) -> ConversationMessage:
        """Adds a message to the pending state:

        - UserMessage is added before sending to stream
        - ConversationMessage (assistant message) is added after stream is complete
        """
        if isinstance(message, UserMessage):
            message = self._convert_user_message(message)

        if message.conversation_id is None:
            raise ValueError("Conversation ID is required")
        await self.redis_repository.rpush_method(message.conversation_id, message)
        logger.info(
            f"Added pending message [role={message.role}] to conversation {message.conversation_id} with message_id "
            f"{message.message_id}"
        )
        return message

    def _convert_user_message(self, message: UserMessage) -> ConversationMessage:
        """Converts a UserMessage to a ConversationMessage by properly converting all content blocks."""
        conversation_message = ConversationMessage(
            message_id=message.message_id,
            conversation_id=message.conversation_id,
            role=Role.USER,
            content=message.content,
        )
        return conversation_message

    async def _create_new_redis_history(self, conversation_id: UUID) -> None:
        """Creates a new conversation history in Redis."""
        conversation = await self.data_service.get_conversation(conversation_id)

        # Create empty history using user_id from Supabase conversation
        history = ConversationHistory(
            conversation_id=conversation_id,
            user_id=conversation.user_id,  # Get from Supabase conversation
        )
        await self.redis_repository.set_method(conversation_id, history)

    async def commit_pending(self, conversation_id: UUID) -> None:
        """Commits pending messages to Redis and Supabase."""
        logger.info(f"Starting commit of pending messages for conversation: {conversation_id}")

        # 1. Ensure history exists in Redis for new conversations
        conversation = await self.redis_repository.get_method(conversation_id, ConversationHistory)
        if not conversation:
            await self._create_new_redis_history(conversation_id)

        # 2. Atomically update conversation history with pending messages
        conversation_history, pending_messages = await self.transfer_pending_to_history(conversation_id)

        # 3. Save data to Supabase
        if conversation_history:
            # 3. Prune and save
            conversation_history = await self._prune_history(conversation_history)
            await self.data_service.update_conversation_supabase(conversation_history, pending_messages)
            logger.info(f"Committed {len(pending_messages)} messages for conversation: {conversation_id}")

    async def clear_pending(self, conversation_id: UUID) -> None:
        """Clears pending messages for a conversation."""
        await self.redis_repository.delete_method(conversation_id, ConversationMessage)

    async def transfer_pending_to_history(
        self, conversation_id: UUID
    ) -> tuple[ConversationHistory, list[ConversationMessage]]:
        """Transfers pending messages to the active conversation in Redis."""
        logger.info(f"Transferring pending messages for conversation: {conversation_id}")
        # Create a pipeline
        client = await self.redis_repository.manager.get_async_client()
        async with client.pipeline(transaction=True) as pipe:
            while True:
                try:
                    # 1. Watch keys
                    messages_key = self.redis_repository._get_prefix(
                        model_class=ConversationMessage, conversation_id=conversation_id
                    )
                    conversation_key = self.redis_repository._get_prefix(
                        model_class=ConversationHistory, conversation_id=conversation_id
                    )
                    await pipe.watch(messages_key, conversation_key)

                    # 2. Get the current state of the conversation and pending messages
                    conversation = await self.redis_repository.get_method(conversation_id, ConversationHistory)
                    if not conversation:
                        # TODO: create a
                        raise ValueError(f"No conversation found for ID {conversation_id}")

                    pending_messages = await self.redis_repository.lrange_method(
                        key=conversation_id, start=0, end=-1, model_class=ConversationMessage
                    )
                    # logger.debug(_truncate_message(f"Pending messages: {pending_messages}"))

                    # 3. Update conversation history
                    conversation.messages.extend(pending_messages)
                    conversation.token_count += await self._estimate_tokens(pending_messages)

                    # 4. Make atomic save & delete
                    pipe.multi()
                    await self.redis_repository.set_method(conversation_id, conversation, pipe=pipe)
                    await self.redis_repository.delete_method(conversation_id, ConversationMessage, pipe=pipe)

                    # 5. Execute transaction
                    await pipe.execute()

                    return conversation, pending_messages
                except redis.WatchError:
                    logger.warning("WatchError during transfer_pending_to_history, retrying...")
                    continue  # Retry the operation
                except Exception as e:
                    logger.error(f"Error transferring pending messages: {e}", exc_info=True)
                    # rollback redis transaction
                    raise

    async def _estimate_tokens(self, messages: list[ConversationMessage]) -> int:
        """Estimates the total token count for a list of messages."""
        total_tokens = 0
        for message in messages:
            for block in message.content:
                if isinstance(block, TextBlock):
                    total_tokens += len(self.tokenizer.encode(block.text))
                    logger.debug(f"Token count for text: {total_tokens}")
                elif isinstance(block, ToolUseBlock):
                    total_tokens += len(self.tokenizer.encode(block.name))
                    total_tokens += len(self.tokenizer.encode(json.dumps(block.input, sort_keys=True)))
                    logger.debug(f"Token count for tool use: {total_tokens}")
                elif isinstance(block, ToolResultBlock):
                    if block.content is not None:
                        if isinstance(block.content, dict):
                            total_tokens += len(self.tokenizer.encode(json.dumps(block.content, sort_keys=True)))
                            logger.debug(f"Token count for tool result: {total_tokens}")
        # logger.debug(f"Total token count: {total_tokens}")
        return total_tokens

    async def _prune_history(self, conversation: ConversationHistory) -> ConversationHistory:
        """Prunes the conversation history if it exceeds the token limit."""
        while conversation.token_count > self.max_tokens * 0.9 and len(conversation.messages) > 1:
            removed_message = conversation.messages.pop(0)
            conversation.token_count -= await self._estimate_tokens([removed_message])

        return conversation

    def _add_message_if_passed(self, history: ConversationHistory, message: UserMessage | None) -> ConversationHistory:
        """Adds a message to the conversation if provided."""
        if message:
            conversation_message = self._convert_user_message(message)
            history.messages.append(conversation_message)
        return history

    async def _get_history_from_redis(self, conversation_id: UUID) -> ConversationHistory | None:
        """Fetch conversation history from Redis.

        Returns:
            ConversationHistory | None: Returns None if key doesn't exist, raises KollektivError for connection issues
        """
        try:
            history = await self.redis_repository.get_method(conversation_id, ConversationHistory)
            if history is None:
                logger.debug(f"No conversation found in Redis for ID: {conversation_id}")
                return None

            # Validate the conversation ID matches
            if history.conversation_id != conversation_id:
                logger.error(
                    f"Redis returned conversation with mismatched ID. "
                    f"Expected: {conversation_id}, Got: {history.conversation_id}"
                )
                return None
            logger.debug(f"Retrieved conversation from Redis with id: {conversation_id}")
            return history

        except RedisError as e:
            logger.error(f"Redis connection error while fetching conversation {conversation_id}: {str(e)}")
            raise KollektivError(f"Failed to fetch conversation from Redis: {str(e)}") from e

    async def _get_history_from_supabase(self, conversation_id: UUID) -> ConversationHistory | None:
        """Builds a conversation history from Conversation Supabase."""
        # Check if conversation exists
        conversation = await self.data_service.get_conversation(conversation_id)
        if conversation is None:
            logger.debug(f"Conversation {conversation_id} not found in Supabase")
            return None

        logger.debug(f"Conversation {conversation_id} found in Supabase")
        # Get messages (can be empty list)
        messages = await self.data_service.get_conversation_messages(conversation_id) or []

        # Create ConversationHistory model
        history = ConversationHistory(conversation_id=conversation_id, messages=messages, user_id=conversation.user_id)

        # Set in redis
        await self.redis_repository.set_method(conversation_id, history)

        # Return
        return history

    async def _create_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        """Creates a new conversation in Supabase."""
        # 1. Create Conversation
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            message_ids=[],
            token_count=0,
        )

        # 3. Save to Supabase
        await self.data_service.save_conversation(conversation)

        return conversation

    async def _create_history(self, conversation_id: UUID, user_id: UUID) -> ConversationHistory:
        """Creates a new conversation history."""
        # Save empty conversation to Supabase
        await self._create_conversation(conversation_id, user_id)
        logger.debug(f"Conversation {conversation_id} created in Supabase")

        # Create a Conversation history object
        history = ConversationHistory(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        return history

    async def get_conversation_history(self, conversation_id: UUID, user_id: UUID) -> ConversationHistory:
        """Get or create a conversation history committed to Redis or Supabase If none found, creates a new one.

        Args:
            conversation_id: The ID of the conversation to fetch/create
            message: Optional user message to add to the conversation

        Returns:
            ConversationHistory: The conversation history, either existing or newly created
        """
        # Try and return from Redis first
        history = await self._get_history_from_redis(conversation_id)
        if history:
            logger.debug(f"Returning history from Redis with n_messages: {len(history.messages)}")
            return history
            # return self._add_message_if_passed(history, message)

        # Try and return from Supabase second
        history = await self._get_history_from_supabase(conversation_id)
        if history:
            logger.debug(f"Returning history from Supabase with n_messages: {len(history.messages)}")
            return history
            # return self._add_message_if_passed(history, message)

        # If neither, build and return from scratch
        history = await self._create_history(conversation_id, user_id)
        logger.debug(f"Created history from scratch with n_messages: {len(history.messages)}")
        return history

    async def _add_pending_messages_to_history(
        self, conversation_id: UUID, history: ConversationHistory
    ) -> ConversationHistory:
        """Retrieves pending messages from Redis (if any) and adds them to the conversation history."""
        pending_messages = await self.redis_repository.lrange_method(
            key=conversation_id, start=0, end=-1, model_class=ConversationMessage
        )
        if pending_messages:
            history.messages.extend(pending_messages)
        return history

    async def setup_new_conv_history_turn(self, message: UserMessage) -> ConversationHistory:
        """Sets up the conversation history for streaming:

        1. Retrieves a new or committed history from Redis or Supabase
        2. Adds the user message to the pending state
        3. Adds all pending messages to the history
        4. Returns the history

        """
        try:
            # 1. Add user message to pending state
            await self.add_pending_message(message=message)

            # 2. Get or create conversation history
            conversation_history = await self.get_conversation_history(
                conversation_id=message.conversation_id, user_id=message.user_id
            )

            # 3. Add all pending messages to the history
            conversation_history = await self._add_pending_messages_to_history(
                conversation_id=message.conversation_id, history=conversation_history
            )

            return conversation_history
        except RedisError as e:
            logger.exception(f"Redis connection error while fetching conversation {message.conversation_id}: {str(e)}")
            raise KollektivError(f"Failed to fetch conversation from Redis: {str(e)}") from e
        except Exception as e:
            logger.exception(f"Error setting up new conversation history turn: {str(e)}")
            raise
