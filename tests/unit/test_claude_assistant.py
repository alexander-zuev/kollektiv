"""Test suite for ClaudeAssistant."""
import aiohttp
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anthropic import RateLimitError
from anthropic.types import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    MessageStopEvent,
    Message
)

from src.core._exceptions import (
    ClientDisconnectError,
    ConnectionError,
    NonRetryableLLMError,
    RetryableLLMError,
    StreamingError,
    TokenLimitError,
)
from src.models.chat_models import ConversationHistory, ConversationMessage, MessageContent, StandardEventType, TextBlock, Role


def test_claude_assistant_initialization(claude_assistant_with_mock):
    """Test that ClaudeAssistant initializes correctly with mocked dependencies."""
    assistant = claude_assistant_with_mock
    assert assistant.client is not None
    assert isinstance(assistant.conversation_history, ConversationHistory)


@pytest.mark.asyncio
async def test_add_message_to_conversation_history(claude_assistant_with_mock):
    """Test adding a message to the conversation history."""
    assistant = claude_assistant_with_mock
    # Clear any existing messages
    assistant.conversation_history = ConversationHistory()

    message = ConversationMessage(
        role="user",
        content=MessageContent(blocks=[TextBlock(text="Test message")])
    )
    # Message is added directly to conversation history
    assistant.conversation_history.messages.append(message)
    assert len(assistant.conversation_history.messages) == 1
    assert assistant.conversation_history.messages[-1] == message


@pytest.mark.asyncio
async def test_update_system_prompt(claude_assistant_with_mock):
    """Test updating the system prompt with document summaries."""
    assistant = claude_assistant_with_mock
    summaries = [{"filename": "doc1", "summary": "Summary 1", "keywords": ["key1", "key2"]}]
    await assistant.update_system_prompt(summaries)
    assert "doc1" in assistant.system_prompt.blocks[0].text


@pytest.mark.asyncio
async def test_get_response(claude_assistant_with_mock):
    """Test getting a response from Claude."""
    assistant = claude_assistant_with_mock
    message = ConversationMessage(
        role="user",
        content=MessageContent(blocks=[TextBlock(text="Test message")])
    )

    # Mock Claude's response for non-streaming case
    mock_response = Message(
        role="assistant",
        content=[{"type": "text", "text": "Test response"}],
        model="claude-3",
        id="msg_123"
    )
    assistant.client.messages.create.return_value = mock_response

    # Get response (non-streaming)
    events = []
    async for event in assistant.get_response(message, stream=False):
        events.append(event)

    # Verify response
    assert len(events) == 1
    assert events[0].event_type == StandardEventType.MESSAGE_COMPLETE
    assert events[0].content == mock_response

    # Verify conversation history was updated
    assert len(assistant.conversation_history.messages) == 2
    assert assistant.conversation_history.messages[-1].role == "user"
    assert assistant.conversation_history.messages[-1].content.blocks[0].text == "Test message"


@pytest.mark.asyncio
async def test_handle_tool_use_rag_search(claude_assistant_with_mock):
    """Test handling of RAG search tool use."""
    assistant = claude_assistant_with_mock

    # Mock the use_rag_search method at the module level where it's called
    expected_search_results = ["Document 1 content", "Document 2 content"]

    # Create a mock for the entire tool use flow
    with patch("src.core.chat.claude_assistant.ClaudeAssistant.use_rag_search", return_value=expected_search_results):
        # Test input that would trigger RAG search
        tool_input = {"important_context": "test context"}
        tool_use_id = "test_tool_id"

        # Execute tool use
        result = assistant.handle_tool_use(tool_name="rag_search", tool_input=tool_input, tool_use_id=tool_use_id)

        # Verify the result format matches Anthropic's expected format
        assert result["role"] == "user"
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "tool_result"
        assert result["content"][0]["tool_use_id"] == tool_use_id

        # Verify the tool result contains the expected search results
        assert "Document 1 content" in result["content"][0]["content"]
        assert "Document 2 content" in result["content"][0]["content"]


@pytest.mark.asyncio
async def test_stream_response_token_limit_error(claude_assistant_with_mock):
    """Test token limit error handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock streaming error
    async def mock_stream():
        yield {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0
                }
            }
        }
        raise TokenLimitError("Token limit exceeded")

    assistant.client.messages.create = AsyncMock(side_effect=mock_stream)

    # Verify token limit error is raised
    with pytest.raises(TokenLimitError):
        async for _ in assistant.stream_response(conversation):
            pass


@pytest.mark.asyncio
async def test_stream_response_connection_error(claude_assistant_with_mock):
    """Test connection error handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock the client to raise a connection error
    assistant.client.messages.create = AsyncMock(side_effect=aiohttp.ClientError())

    # Test that ConnectionError is raised
    with pytest.raises(ConnectionError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass

    assert "Connection error during streaming" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_retryable_error(claude_assistant_with_mock):
    """Test retryable error handling in streaming."""
    from anthropic import APIError

    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock the client to raise a retryable error
    assistant.client.messages.create = AsyncMock(side_effect=APIError("API error"))

    # Test that StreamingError is raised
    with pytest.raises(StreamingError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass

    assert "Unexpected error during streaming" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_successful_flow(claude_assistant_with_mock):
    """Test successful streaming flow."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock streaming events with proper schema
    events = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0
                }
            }
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": "Test response"
            }
        },
        {
            "type": "message_stop",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Test response"}],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5
                }
            }
        }
    ]

    async def mock_stream():
        for event in events:
            yield event

    assistant.client.messages.create = AsyncMock(side_effect=mock_stream)

    # Collect events from streaming
    received_events = []
    async for event in assistant.stream_response(conversation):
        received_events.append(event)

    # Verify event sequence
    assert len(received_events) == 3
    assert received_events[0].event_type == StandardEventType.MESSAGE_START
    assert received_events[1].event_type == StandardEventType.TEXT_TOKEN
    assert received_events[1].content == "Test response"
    assert received_events[2].event_type == StandardEventType.MESSAGE_STOP


@pytest.mark.asyncio
async def test_stream_response_client_disconnect(claude_assistant_with_mock):
    """Test client disconnect handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock streaming events with disconnect
    async def mock_stream():
        yield {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "model": "claude-3-sonnet-20240229",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0
                }
            }
        }
        yield {
            "type": "content_block_delta",
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": "Test"
            }
        }
        raise ClientDisconnectError("Client disconnected")

    assistant.client.messages.create = AsyncMock(side_effect=mock_stream)

    # Verify client disconnect error is raised
    with pytest.raises(ClientDisconnectError):
        async for _ in assistant.stream_response(conversation):
            pass
