from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
)


class TestRedisRepository:
    """Unit tests for RedisRepository."""

    async def test_set_get_conversation(self, redis_repository, sample_conversation, sample_uuid, mock_async_redis):
        """Test setting and getting a conversation."""
        json_str = redis_repository._to_json(sample_conversation)
        mock_async_redis.get.return_value = json_str

        # Test set operation with TTL
        await redis_repository.set_method(sample_uuid, sample_conversation)
        mock_async_redis.set.assert_awaited_once_with(
            f"conversations:{sample_uuid}:history",
            json_str,
            ex=60 * 60 * 24,  # 1 day TTL
        )

        # Test get operation
        result = await redis_repository.get_method(sample_uuid, ConversationHistory)
        assert result is not None
        assert result.conversation_id == sample_conversation.conversation_id
        assert len(result.messages) == len(sample_conversation.messages)
        assert result.messages[0].content[0].text == sample_conversation.messages[0].content[0].text

    async def test_message_queue_operations(self, redis_repository, sample_message, sample_uuid, mock_async_redis):
        """Test message queue operations (rpush, lrange, lpop, rpop)."""
        json_str = redis_repository._to_json(sample_message)
        mock_async_redis.lrange.return_value = [json_str]
        mock_async_redis.lpop.return_value = json_str
        mock_async_redis.rpop.return_value = json_str
        mock_async_redis.expire = AsyncMock()

        # Test rpush with TTL
        await redis_repository.rpush_method(sample_uuid, sample_message)
        mock_async_redis.rpush.assert_awaited_once()
        mock_async_redis.expire.assert_awaited_once_with(
            f"conversations:{sample_uuid}:pending_messages",
            60 * 60,  # 1 hour TTL
        )

        # Test lrange
        messages = await redis_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(messages) == 1
        assert messages[0].message_id == sample_message.message_id
        assert messages[0].role == sample_message.role
        assert messages[0].content[0].text == sample_message.content[0].text

        # Test lpop
        popped = await redis_repository.lpop_method(sample_uuid, ConversationMessage)
        assert popped is not None
        assert popped.message_id == sample_message.message_id
        assert popped.role == sample_message.role

        # Test rpop
        popped = await redis_repository.rpop_method(sample_uuid, ConversationMessage)
        assert popped is not None
        assert popped.message_id == sample_message.message_id
        assert popped.role == sample_message.role

        # Test empty list behavior
        mock_async_redis.lpop.return_value = None
        mock_async_redis.rpop.return_value = None
        empty_lpop = await redis_repository.lpop_method(sample_uuid, ConversationMessage)
        empty_rpop = await redis_repository.rpop_method(sample_uuid, ConversationMessage)
        assert empty_lpop is None
        assert empty_rpop is None

    async def test_delete_operations(self, redis_repository, sample_uuid, mock_async_redis):
        """Test delete operations for both conversation and messages."""
        # Test delete conversation
        await redis_repository.delete_method(sample_uuid, ConversationHistory)
        mock_async_redis.delete.assert_awaited_with(f"conversations:{sample_uuid}:history")

        # Test delete messages
        await redis_repository.delete_method(sample_uuid, ConversationMessage)
        mock_async_redis.delete.assert_awaited_with(f"conversations:{sample_uuid}:pending_messages")

    async def test_prefix_and_ttl_config(self, redis_repository, sample_uuid):
        """Test prefix generation and TTL configuration."""
        # Test prefix templates
        conv_prefix = redis_repository._get_prefix(ConversationHistory, conversation_id=sample_uuid)
        assert conv_prefix == f"conversations:{sample_uuid}:history"

        msg_prefix = redis_repository._get_prefix(ConversationMessage, conversation_id=sample_uuid)
        assert msg_prefix == f"conversations:{sample_uuid}:pending_messages"

        # Test TTL configuration
        assert redis_repository._get_ttl(ConversationHistory) == 60 * 60 * 24  # 1 day
        assert redis_repository._get_ttl(ConversationMessage) == 60 * 60  # 1 hour
