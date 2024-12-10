"""Integration tests for ChatService."""
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from anthropic.types import (
    MessageStartEvent,
    MessageDeltaEvent,
    MessageStopEvent,
)

from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.conversation_manager import ConversationManager
from src.core.chat.events import StandardEventType
from src.core.chat.exceptions import TokenLimitError, ClientDisconnectError
from src.models.chat_models import (
    ConversationHistory,
    Role,
    StandardEvent,
    StandardEventType,
)
from src.services.chat_service import ChatService
from src.services.data_service import DataService


@pytest.fixture
async def chat_service():
    """Create a ChatService instance with mocked dependencies."""
    claude_assistant = Mock(spec=ClaudeAssistant)
    conversation_manager = Mock(spec=ConversationManager)
    data_service = Mock(spec=DataService)
    data_service.save_conversation = AsyncMock()

    # Setup default conversation
    conversation = ConversationHistory(
        conversation_id=uuid.uuid4(),
        data_sources=[uuid.uuid4()]
    )
    conversation_manager.get_or_create_conversation.return_value = conversation
    conversation_manager.get_conversation_with_pending.return_value = conversation

    return ChatService(
        claude_assistant=claude_assistant,
        conversation_manager=conversation_manager,
        data_service=data_service,
    )


@pytest.mark.asyncio
async def test_complete_streaming_flow(chat_service):
    """Test complete streaming flow with persistence."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message"

    # Mock streaming events with proper schema
    events = [
        MessageStartEvent(
            type="message_start",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-3-sonnet-20240229"
            }
        ),
        MessageDeltaEvent(
            type="message_delta",
            delta={
                "type": "text",
                "text": "Hello world",
            },
            usage={
                "input_tokens": 10,
                "output_tokens": 5
            }
        ),
        MessageStopEvent(
            type="message_stop",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello world"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    ]

    # Setup mock response stream
    async def mock_stream() -> AsyncGenerator:
        for event in events:
            yield event

    chat_service.claude_assistant.stream_response = AsyncMock(side_effect=mock_stream)

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify responses
    assert len(responses) == 3
    assert responses[0].event_type == StandardEventType.MESSAGE_START
    assert responses[1].event_type == StandardEventType.TEXT_TOKEN
    assert responses[1].content == "Hello world"
    assert responses[2].event_type == StandardEventType.MESSAGE_STOP

    # Verify conversation persistence
    chat_service.conversation_manager.commit_pending.assert_called_once_with(conversation_id)
    chat_service.data_service.save_conversation.assert_called_once_with(conversation_id)


@pytest.mark.asyncio
async def test_streaming_error_recovery(chat_service):
    """Test error recovery in streaming flow."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message"

    # Mock streaming error
    async def mock_error_stream():
        if True:  # This ensures the generator yields at least once
            raise TokenLimitError("Test error")
        yield None  # This line is never reached but makes it an async generator
    chat_service.claude_assistant.stream_response = AsyncMock(side_effect=mock_error_stream)

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify error response
    assert len(responses) == 1
    assert responses[0].event_type == StandardEventType.ERROR
    assert "Test error" in responses[0].content

    # Verify cleanup
    chat_service.conversation_manager.rollback_pending.assert_called_once_with(conversation_id)


@pytest.mark.asyncio
async def test_streaming_tool_use_flow(chat_service):
    """Test streaming flow with tool use (RAG search)."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message with RAG"

    # Mock streaming events including tool use
    events = [
        MessageStartEvent(
            type="message_start",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-3-sonnet-20240229"
            }
        ),
        MessageDeltaEvent(
            type="message_delta",
            delta={
                "type": "text",
                "text": "Search result",
            },
            usage={
                "input_tokens": 10,
                "output_tokens": 5
            }
        ),
        MessageStopEvent(
            type="message_stop",
            message={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Search result"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    ]

    # Setup mock response stream
    async def mock_stream() -> AsyncGenerator:
        for event in events:
            yield event

    chat_service.claude_assistant.stream_response = AsyncMock(side_effect=mock_stream)

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify responses
    assert len(responses) == 3
    assert responses[0].event_type == StandardEventType.MESSAGE_START
    assert responses[1].event_type == StandardEventType.TEXT_TOKEN
    assert responses[1].content == "Search result"
    assert responses[2].event_type == StandardEventType.MESSAGE_STOP

    # Verify conversation persistence
    chat_service.conversation_manager.commit_pending.assert_called_once_with(conversation_id)
    chat_service.data_service.save_conversation.assert_called_once_with(conversation_id)

    # Verify tool use was added to conversation
    chat_service.conversation_manager.add_pending_message.assert_any_call(
        conversation_id=conversation_id,
        role=Role.ASSISTANT,
        text="rag_search"
    )
