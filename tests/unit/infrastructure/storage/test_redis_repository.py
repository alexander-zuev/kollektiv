import pytest

from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    TextBlock,
)


class TestRedisRepository:
    """Unit tests for RedisRepository using fakeredis."""

    async def test_set_get_conversation(self, redis_repository, sample_conversation, sample_uuid):
        """Test setting and getting a conversation."""
        # Test set operation
        await redis_repository.set_method(sample_uuid, sample_conversation)

        # Test get operation
        result = await redis_repository.get_method(sample_uuid, ConversationHistory)
        assert result is not None
        assert result.conversation_id == sample_conversation.conversation_id
        assert len(result.messages) == len(sample_conversation.messages)

    async def test_message_queue_operations(self, redis_repository, sample_message, sample_uuid):
        """Test message queue operations (rpush, lrange)."""
        # Test rpush
        await redis_repository.rpush_method(sample_uuid, sample_message)

        # Test lrange
        messages = await redis_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(messages) == 1
        assert messages[0].message_id == sample_message.message_id
        assert messages[0].role == sample_message.role

        # Test delete
        await redis_repository.delete_method(sample_uuid)
        messages = await redis_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(messages) == 0

    async def test_prefix_generation(self, redis_repository, sample_uuid):
        """Test key prefix generation for different models."""
        # Test conversation history prefix
        conv_prefix = redis_repository._get_prefix(ConversationHistory, conversation_id=sample_uuid)
        assert conv_prefix == f"conversations:{sample_uuid}:history"

        # Test message prefix
        msg_prefix = redis_repository._get_prefix(ConversationMessage, conversation_id=sample_uuid)
        assert msg_prefix == f"conversations:{sample_uuid}:pending_messages"

        # Test invalid model
        with pytest.raises(ValueError):
            redis_repository._get_prefix(TextBlock, conversation_id=sample_uuid)
