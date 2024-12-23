import uuid

import pytest

from src.models.chat_models import ConversationHistory, ConversationMessage, Role, TextBlock


@pytest.mark.integration
class TestRedisRepositoryIntegration:
    """Integration tests requiring real Redis server."""

    async def test_conversation_lifecycle(self, redis_integration_repository, sample_conversation, sample_uuid):
        """Test complete conversation lifecycle with real Redis."""
        # Store conversation
        await redis_integration_repository.set_method(sample_uuid, sample_conversation)

        # Retrieve and verify
        retrieved = await redis_integration_repository.get_method(sample_uuid, ConversationHistory)
        assert retrieved is not None
        assert retrieved.conversation_id == sample_conversation.conversation_id
        assert len(retrieved.messages) == len(sample_conversation.messages)

        # Delete
        await redis_integration_repository.delete_method(sample_uuid, ConversationHistory)

        # Verify deletion
        deleted = await redis_integration_repository.get_method(sample_uuid, ConversationHistory)
        assert deleted is None

    async def test_message_queue_workflow(self, redis_integration_repository, sample_uuid):
        """Test real message queueing workflow."""
        # Create test messages
        messages = [
            ConversationMessage(
                message_id=uuid.uuid4(),
                role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
                content=[TextBlock(text=f"Message {i}")],
            )
            for i in range(3)
        ]

        # Push messages to queue
        for msg in messages:
            await redis_integration_repository.rpush_method(sample_uuid, msg)

        # Retrieve all messages
        retrieved = await redis_integration_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(retrieved) == len(messages)

        # Verify order and content
        for original, retrieved_msg in zip(messages, retrieved, strict=False):
            assert retrieved_msg.role == original.role
            assert retrieved_msg.content[0].text == original.content[0].text

        # Test pop operations
        first = await redis_integration_repository.lpop_method(sample_uuid, ConversationMessage)
        assert first is not None
        assert first.content[0].text == "Message 0"

        last = await redis_integration_repository.rpop_method(sample_uuid, ConversationMessage)
        assert last is not None
        assert last.content[0].text == "Message 2"

        # Verify remaining message
        remaining = await redis_integration_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(remaining) == 1
        assert remaining[0].content[0].text == "Message 1"

    async def test_pipeline_operations(self, redis_integration_repository, sample_uuid):
        """Test pipeline operations for atomic updates."""
        # 1. Setup
        initial_message = ConversationMessage(
            message_id=uuid.uuid4(), role=Role.USER, content=[TextBlock(text="Initial message")]
        )
        conversation = ConversationHistory(conversation_id=sample_uuid, messages=[initial_message])
        await redis_integration_repository.set_method(sample_uuid, conversation)

        pending_messages = [
            ConversationMessage(
                message_id=uuid.uuid4(), role=Role.ASSISTANT, content=[TextBlock(text="Pending message 1")]
            ),
            ConversationMessage(message_id=uuid.uuid4(), role=Role.USER, content=[TextBlock(text="Pending message 2")]),
        ]
        for msg in pending_messages:
            await redis_integration_repository.rpush_method(sample_uuid, msg)

        # 2. Pipeline Operation
        async with redis_integration_repository.client.pipeline(transaction=True) as pipe:
            # Retrieve conversation and pending messages
            retrieved_conversation = await redis_integration_repository.get_method(sample_uuid, ConversationHistory)
            retrieved_pending_messages = await redis_integration_repository.lrange_method(
                sample_uuid, 0, -1, ConversationMessage
            )

            # Extend conversation history
            retrieved_conversation.messages.extend(retrieved_pending_messages)

            # Save updated conversation and delete pending messages
            await redis_integration_repository.set_method(sample_uuid, retrieved_conversation, pipe=pipe)
            await redis_integration_repository.delete_method(sample_uuid, ConversationMessage, pipe=pipe)

            # Execute pipeline
            await pipe.execute()

        # 3. Verification
        updated_conversation = await redis_integration_repository.get_method(sample_uuid, ConversationHistory)
        assert updated_conversation is not None
        assert len(updated_conversation.messages) == 3  # Initial + 2 pending
        assert updated_conversation.messages[0].content[0].text == "Initial message"
        assert updated_conversation.messages[1].content[0].text == "Pending message 1"
        assert updated_conversation.messages[2].content[0].text == "Pending message 2"

        remaining_messages = await redis_integration_repository.lrange_method(sample_uuid, 0, -1, ConversationMessage)
        assert len(remaining_messages) == 0
