"""Integration tests for ChatService."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core._exceptions import ClientDisconnectError, TokenLimitError
from src.core.chat.events import StandardEventType
from src.models.chat_models import ConversationHistory, MessageContent, Role, TextBlock
from src.services.chat_service import ChatService


@pytest.fixture
def chat_service():
    """Create a ChatService instance with mocked dependencies."""
    claude_assistant = MagicMock()
    claude_assistant.stream_response = AsyncMock()
    return ChatService(claude_assistant=claude_assistant)


@pytest.mark.asyncio
async def test_complete_streaming_flow(chat_service):
    """Test complete streaming flow with proper event sequence."""
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock streaming events
    events = [
        {
            "event_type": StandardEventType.MESSAGE_START,
            "content": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        },
        {
            "event_type": StandardEventType.TEXT_TOKEN,
            "content": "Test response"
        },
        {
            "event_type": StandardEventType.MESSAGE_STOP,
            "content": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Test response"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5}
            }
        }
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event

    chat_service.claude_assistant.stream_response.side_effect = mock_stream

    # Collect events from streaming
    received_events = []
    async for event in chat_service.get_response(conversation):
        received_events.append(event)

    # Verify event sequence
    assert len(received_events) == 3
    assert received_events[0].event_type == StandardEventType.MESSAGE_START
    assert received_events[1].event_type == StandardEventType.TEXT_TOKEN
    assert received_events[1].content == "Test response"
    assert received_events[2].event_type == StandardEventType.MESSAGE_STOP


@pytest.mark.asyncio
async def test_streaming_error_recovery(chat_service):
    """Test error recovery in streaming flow."""
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock streaming events with error
    events = [
        {
            "event_type": StandardEventType.MESSAGE_START,
            "content": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        }
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event
        raise TokenLimitError("Token limit exceeded")

    chat_service.claude_assistant.stream_response.side_effect = mock_stream

    # Verify error handling
    with pytest.raises(TokenLimitError):
        async for event in chat_service.get_response(conversation):
            assert event.event_type == StandardEventType.MESSAGE_START


@pytest.mark.asyncio
async def test_streaming_tool_use_flow(chat_service):
    """Test streaming flow with tool use."""
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Search for test")

    # Mock streaming events with tool use
    events = [
        {
            "event_type": StandardEventType.MESSAGE_START,
            "content": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 10, "output_tokens": 0}
            }
        },
        {
            "event_type": StandardEventType.TOOL_START,
            "content": {
                "type": "tool_use",
                "tool_name": "rag_search",
                "tool_input": {"query": "test"},
                "tool_use_id": "tool_1"
            }
        },
        {
            "event_type": StandardEventType.TOOL_RESULT,
            "content": {
                "type": "tool_result",
                "tool_use_id": "tool_1",
                "content": "Search result"
            }
        },
        {
            "event_type": StandardEventType.MESSAGE_STOP,
            "content": {
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
        }
    ]

    async def mock_stream(conversation):
        for event in events:
            yield event

    chat_service.claude_assistant.stream_response.side_effect = mock_stream

    # Collect events from streaming
    received_events = []
    async for event in chat_service.get_response(conversation):
        received_events.append(event)

    # Verify event sequence
    assert len(received_events) == 4
    assert received_events[0].event_type == StandardEventType.MESSAGE_START
    assert received_events[1].event_type == StandardEventType.TOOL_START
    assert received_events[2].event_type == StandardEventType.TOOL_RESULT
    assert received_events[3].event_type == StandardEventType.MESSAGE_STOP
