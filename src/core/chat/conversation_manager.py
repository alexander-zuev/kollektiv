import json
from uuid import UUID

import redis
import tiktoken

from src.api.v0.schemas.chat_schemas import UserMessage
from src.infrastructure.common.logger import get_logger
from src.infrastructure.storage.redis_repository import RedisRepository
from src.models.chat_models import (
    Conversation,
    ConversationHistory,
    ConversationMessage,
    Role,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
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

    async def create_conversation(self, message: UserMessage) -> ConversationHistory:
        """Creates a new conversation history."""
        # 1. Create an empty conversation
        conversation = ConversationHistory()
        logger.info(f"Creating new conversation with ID: {conversation.conversation_id}")

        # 2. Save empty converstaion to redis
        await self.redis_repository.set_method(conversation.conversation_id, conversation)
        logger.debug(f"Initialized empty conversation in Redis: {conversation.model_dump()}")

        # 3. Create a conversation in Supabase
        # create a title
        title = f"Conversation {conversation.conversation_id}"
        supabase_conversation = Conversation(
            conversation_id=conversation.conversation_id,
            user_id=message.user_id,
            title=title,
            message_ids=[],
            token_count=0,
            data_sources=[],
        )
        await self.data_service.save_conversation(supabase_conversation)

        # 3. Add message to in-memory conversation
        conversation_message = await self._convert_user_message(message)
        conversation.messages.append(conversation_message)
        logger.info(f"Added initial message to conversation {conversation.conversation_id}")

        return conversation

    async def add_pending_message(self, message: ConversationMessage | UserMessage) -> ConversationMessage:
        """Adds a message to the pending state during tool use."""
        if isinstance(message, UserMessage):
            message = await self._convert_user_message(message)

        if message.conversation_id is None:
            raise ValueError("Conversation ID is required")
        await self.redis_repository.rpush_method(message.conversation_id, message)
        logger.info(
            f"Added pending message [role={message.role}] to conversation {message.conversation_id} with message_id "
            f"{message.message_id}"
        )
        logger.debug(f"Pending message details: {message.model_dump()}")
        return message

    async def _convert_user_message(self, message: UserMessage) -> ConversationMessage:
        """Converts a UserMessage to a ConversationMessage by properly converting all content blocks."""
        conversation_message = ConversationMessage(
            message_id=message.message_id,
            conversation_id=message.conversation_id,
            role=Role.USER,
            content=message.content,
        )
        logger.debug(f"conversation_message: {conversation_message.model_dump(serialize_as_any=True)}")
        return conversation_message

    async def commit_pending(self, conversation_id: UUID) -> None:
        """Commits pending messages to Redis and Supabase."""
        logger.info(f"Starting commit of pending messages for conversation: {conversation_id}")

        # 1. Atomically update conversation history with pending messages
        conversation_history, pending_messages = await self.transfer_pending_to_history(conversation_id)

        # 2. Save data to Supabase
        if conversation_history:
            # 3. Prune and save
            conversation_history = await self._prune_history(conversation_history)
            await self._update_conversation_supabase(history=conversation_history, messages=pending_messages)
            logger.info(f"Committed {len(pending_messages)} messages for conversation: {conversation_id}")

    async def transfer_pending_to_history(
        self, conversation_id: UUID
    ) -> tuple[ConversationHistory, list[ConversationMessage]]:
        """Transfers pending messages to the active conversation in Redis."""
        logger.info(f"Transferring pending messages for conversation: {conversation_id}")
        # Create a pipeline
        async with self.redis_repository.client.pipeline(transaction=True) as pipe:
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
                        raise ValueError(f"No conversation found for ID {conversation_id}")

                    pending_messages = await self.redis_repository.lrange_method(
                        key=conversation_id, start=0, end=-1, model_class=ConversationMessage
                    )
                    logger.debug(f"Pending messages: {pending_messages}")

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

    async def _update_conversation_supabase(
        self, history: ConversationHistory, messages: list[ConversationMessage]
    ) -> None:
        """Updates the conversation in Supabase."""
        await self.data_service.update_conversation_supabase(history, messages)

    async def _estimate_tokens(self, messages: list[ConversationMessage]) -> int:
        """Estimates the total token count for a list of messages."""
        total_tokens = 0
        for message in messages:
            for block in message.content:
                if isinstance(block, TextBlock):
                    total_tokens += len(self.tokenizer.encode(block.text))
                    logger.debug(f"Token count for text: {total_tokens}")
                elif isinstance(block, ToolUseBlock):
                    total_tokens += len(self.tokenizer.encode(block.tool_name))
                    total_tokens += len(self.tokenizer.encode(json.dumps(block.tool_input, sort_keys=True)))
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

    async def get_conversation_history(
        self, conversation_id: UUID, message: UserMessage | None = None
    ) -> ConversationHistory:
        """Fetches a conversation from Redis or Supabase, if not found in Redis."""
        conversation = await self.redis_repository.get_method(conversation_id, ConversationHistory)

        # If no conversation in Redis, fetch from Supabase
        if conversation is None:
            logger.info(f"Conversation {conversation_id} not found in Redis, fetching from Supabase")
            conversation = await self.data_service.get_conversation_history(conversation_id)

        # Add message to the conversation in-memory
        if message:
            conversation_message = await self._convert_user_message(message)
            conversation.messages.append(conversation_message)

        return conversation
