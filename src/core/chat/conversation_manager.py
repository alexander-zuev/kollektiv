# TODO: refactor token counting https://github.com/anthropics/anthropic-sdk-python?tab=readme-ov-file#token-counting
from uuid import UUID

import tiktoken
from pydantic import ValidationError

from src.core._exceptions import ConversationNotFoundError
from src.infrastructure.common.logger import get_logger
from src.infrastructure.storage.redis_repository import RedisRepository
from src.models.chat_models import ContentBlock, ConversationHistory, ConversationMessage, Role
from src.services.data_service import DataService

logger = get_logger()


class ConversationManager:
    """Manages conversation state, including in-memory storage and token management."""

    def __init__(
        self,
        max_tokens: int = 200000,
        tokenizer: str = "cl100k_base",
        redis_repository: RedisRepository | None = None,
        data_service: DataService | None = None,
    ):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding(tokenizer)
        # Redis
        self.redis_repository = redis_repository
        # Main conversation storage
        self.conversations: dict[UUID, ConversationHistory] = {}
        # Temporary storage for messages during tool use
        self.pending_messages: dict[UUID, list[ConversationMessage]] = {}
        self.data_service = data_service

    async def get_or_create_conversation(self, conversation_id: UUID | None = None) -> ConversationHistory:
        """
        Get or create conversation history by ID.

        Args:
            conversation_id: Optional UUID for the conversation. If None, creates a new conversation
                           with a generated UUID.
        """
        # Create new conversation if no ID is provided
        try:
            if conversation_id is None:
                conversation = await self.create_conversation()
                logger.info(f"Created new conversation: {conversation.conversation_id}")
                return conversation

            # Try to get existing conversation
            else:
                # Try redis first
                conversation = await self.redis_repository.get_method(conversation_id, ConversationHistory)
                if not conversation:
                    conversation = await self.data_service.get_conversation_history(conversation_id)
                return conversation
        except ConversationNotFoundError:
            logger.error(f"Conversation with id {conversation_id} not found", exc_info=True)
            raise

    async def create_conversation(self, conversation_id: UUID | None = None) -> ConversationHistory:
        """Create a new conversation history with auto-generated UUID."""
        if conversation_id is None:
            conversation = ConversationHistory()
        else:
            conversation = ConversationHistory(conversation_id=conversation_id)

        # Add empty conversation to Redis
        self.redis_repository.set_method(conversation.conversation_id, conversation)
        logger.info(f"Created new conversation: {conversation.conversation_id}")
        return conversation
        # Do I need to save it to Supabase at this time?

    async def add_message_to_conversation(self, conversation_id: UUID, role: Role, content: list[ContentBlock]) -> None:
        """Add a message directly to conversation history."""
        try:
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                logger.error(f"No conversation found for {conversation_id}", exc_info=True)
                raise ValueError(f"Conversation {conversation_id} not found")

            message = self._create_message_object(conversation_id, role, content)

            logger.debug(f"Adding message: {message}")
            conversation.messages.append(message)

            # Update token count
            token_count = await self._estimate_tokens(content)
            conversation.token_count += token_count

            # Prune if needed
            await self._prune_history(conversation)

            logger.debug(f"Conversation length after adding a message: {len(conversation.messages)}")
        except ValidationError as e:
            logger.error(f"Error adding message: {e}, {conversation_id}, {role}, {content}", exc_info=True)
            raise

    async def add_message_to_pending_conversation(
        self, conversation_id: UUID, role: Role, content: list[ContentBlock]
    ) -> ConversationMessage:
        """Add message to pending state during tool use."""
        if conversation_id not in self.pending_messages:
            self.pending_messages[conversation_id] = []

        message = self._create_message_object(conversation_id, role, content)
        logger.debug(f"Adding pending message: {message}")
        self.pending_messages[conversation_id].append(message)
        logger.info(f"Added pending {role} message to conversation {conversation_id}: {message.content}")
        return message

    def _create_message_object(
        self, conversation_id: UUID, role: Role, content: list[ContentBlock]
    ) -> ConversationMessage:
        return ConversationMessage(conversation_id=conversation_id, role=role, content=content)

    async def commit_pending(self, conversation_id: UUID) -> None:
        """Commit pending messages to conversation history."""
        # Log the number of pending messages *before* popping
        num_pending_messages = len(self.pending_messages.get(conversation_id, []))
        logger.debug(f"Number of pending messages: {num_pending_messages}")

        if pending := self.pending_messages.pop(conversation_id, None):
            conversation = self.conversations.get(conversation_id)
            if conversation:
                conversation.messages.extend(pending)
                # Update token count
                for message in pending:
                    conversation.token_count += await self._estimate_tokens(message.content)
                await self._prune_history(conversation)

        # Log the updated number of messages in the conversation
        if conversation_id in self.conversations:
            logger.debug(
                f"Number of messages in current conversation: {len(self.conversations[conversation_id].messages)}"
            )
        else:
            logger.debug(f"Conversation {conversation_id} not found after commit_pending.")

    async def rollback_pending(self, conversation_id: UUID) -> None:
        """Discard pending messages."""
        self.pending_messages.pop(conversation_id, None)

    async def _estimate_tokens(self, content: list[ContentBlock]) -> int:
        """Estimate token count for content."""
        if isinstance(content, str):
            return len(self.tokenizer.encode(content))
        elif isinstance(content, list):
            return sum(
                len(self.tokenizer.encode(item["text"]))
                for item in content
                if isinstance(item, dict) and "text" in item
            )
        return 0

    async def _prune_history(self, conversation: ConversationHistory) -> None:
        """Prune conversation history if it exceeds token limit."""
        while conversation.token_count > self.max_tokens * 0.9 and len(conversation.messages) > 1:
            removed_message = conversation.messages.pop(0)
            conversation.token_count -= await self._estimate_tokens(removed_message.content)

    async def get_conversation_with_pending(self, conversation_id: UUID | None) -> ConversationHistory:
        """
        Get a conversation history that includes both stable and pending messages.
        This creates a temporary copy for sending to the LLM.
        """
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Create a copy of stable conversation
        combined = ConversationHistory(
            conversation_id=conversation.conversation_id,
            messages=conversation.messages.copy(),
            token_count=conversation.token_count,
        )

        # Add pending messages
        pending = self.pending_messages.get(conversation_id)
        if pending:
            combined.messages.extend(pending)

        return combined
