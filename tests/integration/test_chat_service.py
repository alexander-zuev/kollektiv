"""Integration tests for ChatService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.core._exceptions import ClientDisconnectError, TokenLimitError
from src.core.chat.events import StandardEvent, StandardEventType
from src.core.chat.conversation_manager import ConversationManager
from src.models.chat_models import ConversationHistory, MessageContent, Role, TextBlock
from src.services.chat_service import ChatService
from src.services.data_service import DataService
from src.api.v0.schemas.chat_schemas import MessageType


@pytest.fixture
def chat_service():
    """Create a ChatService instance with mocked dependencies."""
    claude_assistant = MagicMock()
    claude_assistant.stream_response = AsyncMock()

    conversation_manager = MagicMock(spec=ConversationManager)
    conversation_manager.get_or_create_conversation.return_value = ConversationHistory(conversation_id=UUID("87654321-4321-8765-4321-876543210987"))
    conversation_manager.get_conversation_with_pending.return_value = ConversationHistory(conversation_id=UUID("87654321-4321-8765-4321-876543210987"))

    data_service = MagicMock(spec=DataService)
    data_service.save_conversation = AsyncMock()

    return ChatService(
        claude_assistant=claude_assistant,
        conversation_manager=conversation_manager,
        data_service=data_service
    )


@pytest.mark.asyncio
async def test_complete_streaming_flow(chat_service):
    """Test complete streaming flow with proper event sequence."""
    # Create test data
    user_id = UUID("12345678-1234-5678-1234-567812345678")
    message = "Test message"
    conversation_id = UUID("87654321-4321-8765-4321-876543210987")

    # Mock conversation manager methods
    chat_service.conversation_manager.get_or_create_conversation.return_value = ConversationHistory(conversation_id=conversation_id)
    chat_service.conversation_manager.get_conversation_with_pending.return_value = ConversationHistory(conversation_id=conversation_id)

    # Mock streaming events
    events = [
        StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        ),
        StandardEvent(
            event_type=StandardEventType.TEXT_TOKEN,
            content="Test response"
        ),
        StandardEvent(
            event_type=StandardEventType.MESSAGE_STOP,
            content={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Test response"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event

    # Set up the stream_response method to return an async generator
    chat_service.claude_assistant.stream_response = AsyncMock(
        __aiter__=lambda self: mock_stream(None),
        side_effect=mock_stream
    )

    # Collect events from streaming
    received_events = []
    async for event in chat_service.get_response(user_id=user_id, message=message, conversation_id=conversation_id):
        received_events.append(event)

    # Verify event sequence
    assert len(received_events) == 3
    assert received_events[0].message_type == MessageType.MESSAGE_START
    assert received_events[1].message_type == MessageType.TEXT_TOKEN
    assert received_events[1].text == "Test response"
    assert received_events[2].message_type == MessageType.MESSAGE_STOP


@pytest.mark.asyncio
async def test_streaming_error_recovery(chat_service):
    """Test error recovery in streaming flow."""
    # Create test data
    user_id = UUID("12345678-1234-5678-1234-567812345678")
    message = "Test message"
    conversation_id = UUID("87654321-4321-8765-4321-876543210987")

    # Mock conversation manager methods
    chat_service.conversation_manager.get_or_create_conversation.return_value = ConversationHistory(conversation_id=conversation_id)
    chat_service.conversation_manager.get_conversation_with_pending.return_value = ConversationHistory(conversation_id=conversation_id)

    # Mock streaming events with error
    events = [
        StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        )
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event
        raise TokenLimitError("Token limit exceeded")

    # Set up the stream_response method to return an async generator
    chat_service.claude_assistant.stream_response = AsyncMock(
        __aiter__=lambda self: mock_stream(None),
        side_effect=mock_stream
    )

    # Collect events and verify error handling
    received_events = []
    async for event in chat_service.get_response(user_id=user_id, message=message, conversation_id=conversation_id):
        received_events.append(event)

    # Verify events
    assert len(received_events) == 2
    assert received_events[0].message_type == MessageType.MESSAGE_START
    assert received_events[1].message_type == MessageType.ERROR
    assert "Token limit exceeded" in received_events[1].text


@pytest.mark.asyncio
async def test_streaming_tool_use_flow(chat_service):
    """Test streaming flow with tool use."""
    # Create test data
    user_id = UUID("12345678-1234-5678-1234-567812345678")
    message = "Search for test"
    conversation_id = UUID("87654321-4321-8765-4321-876543210987")

    # Mock conversation manager methods
    chat_service.conversation_manager.get_or_create_conversation.return_value = ConversationHistory(conversation_id=conversation_id)
    chat_service.conversation_manager.get_conversation_with_pending.return_value = ConversationHistory(conversation_id=conversation_id)

    # Mock streaming events with tool use
    events = [
        StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        ),
        StandardEvent(
            event_type=StandardEventType.TOOL_START,
            content={
                "type": "tool_use",
                "tool_name": "rag_search",
                "tool_input": {"query": "test"},
                "tool_use_id": "tool_1"
            }
        ),
        StandardEvent(
            event_type=StandardEventType.TOOL_END,
            content={
                "type": "tool_result",
                "tool_use_id": "tool_1",
                "content": "Search result"
            }
        ),
        StandardEvent(
            event_type=StandardEventType.MESSAGE_STOP,
            content={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Search result"}
                ],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        )
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event

    # Set up the stream_response method to return an async generator
    chat_service.claude_assistant.stream_response = AsyncMock(
        __aiter__=lambda self: mock_stream(None),
        side_effect=mock_stream
    )

    # Collect events from streaming
    received_events = []
    async for event in chat_service.get_response(user_id=user_id, message=message, conversation_id=conversation_id):
        received_events.append(event)

    # Verify event sequence
    assert len(received_events) == 4
    assert received_events[0].message_type == MessageType.MESSAGE_START
    assert received_events[1].message_type == MessageType.TOOL_START
    assert received_events[2].message_type == MessageType.TOOL_END
    assert received_events[3].message_type == MessageType.MESSAGE_STOP
