"""Test suite for ClaudeAssistant."""
import aiohttp
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anthropic.types import Message

from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.exceptions import ConnectionError, StreamingError, TokenLimitError
from src.models.chat_models import ConversationHistory, ConversationMessage, MessageContent, StandardEventType, TextBlock


def test_claude_assistant_initialization(claude_assistant_with_mock):
    """Test that ClaudeAssistant initializes correctly with mocked dependencies."""
    assistant = claude_assistant_with_mock
    assert assistant.client is not None
    assert isinstance(assistant.conversation_history, ConversationHistory)


@pytest.mark.asyncio
async def test_add_message_to_conversation_history(claude_assistant_with_mock):
    """Test adding a message to the conversation history."""
    assistant = claude_assistant_with_mock
    message = ConversationMessage(
        role="user",
        content=MessageContent(blocks=[TextBlock(text="Test message")])
    )
    # Message is added directly to conversation history
    assistant.conversation_history.messages.append(message)
    assert len(assistant.conversation_history.messages) == 2  # Including initial message
    assert assistant.conversation_history.messages[-1] == message


@pytest.mark.asyncio
async def test_update_system_prompt(claude_assistant_with_mock):
    """Test updating the system prompt with document summaries."""
    assistant = claude_assistant_with_mock
    summaries = [{"filename": "doc1", "summary": "Summary 1", "keywords": ["key1", "key2"]}]
    await assistant.update_system_prompt(summaries)
    assert "doc1" in assistant.system_prompt.content.blocks[0].text


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
    history = ConversationHistory()
    history.messages.append(
        ConversationMessage(
            role="user",
            content=MessageContent(blocks=[TextBlock(text="Test message")])
        )
    )

    class MockStream:
        async def __aiter__(self):
            raise NonRetryableLLMError("Token limit exceeded")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    assistant.client.messages.stream.return_value = MockStream()

    with pytest.raises(TokenLimitError):
        async for _ in assistant.stream_response(history):
            pass


@pytest.mark.asyncio
async def test_stream_response_connection_error(claude_assistant_with_mock):
    """Test connection error handling in streaming."""
    assistant = claude_assistant_with_mock
    history = ConversationHistory()
    history.messages.append(
        ConversationMessage(
            role="user",
            content=MessageContent(blocks=[TextBlock(text="Test message")])
        )
    )

    class MockStream:
        async def __aiter__(self):
            raise ConnectionError("Connection failed")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    assistant.client.messages.stream.return_value = MockStream()

    with pytest.raises(ConnectionError):
        async for _ in assistant.stream_response(history):
            pass


@pytest.mark.asyncio
async def test_stream_response_retryable_error(claude_assistant_with_mock):
    """Test retryable error handling in streaming."""
    assistant = claude_assistant_with_mock
    history = ConversationHistory()
    history.messages.append(
        ConversationMessage(
            role="user",
            content=MessageContent(blocks=[TextBlock(text="Test message")])
        )
    )

    class MockStream:
        async def __aiter__(self):
            raise RetryableLLMError("Temporary error")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    assistant.client.messages.stream.return_value = MockStream()

    with pytest.raises(StreamingError):
        async for _ in assistant.stream_response(history):
            pass


@pytest.mark.asyncio
async def test_stream_response_successful_flow(claude_assistant_with_mock):
    """Test successful streaming flow."""
    assistant = claude_assistant_with_mock
    history = ConversationHistory()
    history.messages.append(
        ConversationMessage(
            role="user",
            content=MessageContent(blocks=[TextBlock(text="Test message")])
        )
    )

    # Create a proper async context manager for streaming
    class MockStream:
        def __init__(self):
            self.events = [
                type('Event', (), {"type": "message_start"})(),
                type('Event', (), {
                    "type": "content_block_delta",
                    "delta": type('Delta', (), {"text": "Test"})()
                })(),
                type('Event', (), {
                    "type": "content_block_delta",
                    "delta": type('Delta', (), {"text": " response"})()
                })(),
                type('Event', (), {
                    "type": "message_delta",
                    "delta": type('Delta', (), {"stop_reason": "end_turn"})()
                })()
            ]
            self._index = 0

        async def __aiter__(self):
            for event in self.events:
                yield event

        async def get_final_message(self):
            return Message(
                role="assistant",
                content=[{"type": "text", "text": "Test response"}],
                model="claude-3",
                id="msg_123"
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Set up mock
    assistant.client.messages.stream.return_value = MockStream()

    # Test streaming
    events = []
    async for event in assistant.stream_response(history):
        events.append(event)

    # Verify events
    assert len(events) == 5
    assert events[0].event_type == StandardEventType.MESSAGE_START
    assert events[1].event_type == StandardEventType.TEXT_TOKEN
    assert events[2].event_type == StandardEventType.TEXT_TOKEN
    assert events[3].event_type == StandardEventType.MESSAGE_STOP
    assert events[4].event_type == StandardEventType.MESSAGE_COMPLETE


@pytest.mark.asyncio
async def test_stream_response_client_disconnect(claude_assistant_with_mock):
    """Test client disconnect handling in streaming."""
    assistant = claude_assistant_with_mock
    history = ConversationHistory()
    history.messages.append(
        ConversationMessage(
            role="user",
            content=MessageContent(blocks=[TextBlock(text="Test message")])
        )
    )

    class MockClientError(aiohttp.ClientError):
        pass

    class MockStream:
        async def __aiter__(self):
            yield type('Event', (), {"type": "message_start"})()
            yield type('Event', (), {
                "type": "content_block_delta",
                "delta": {"type": "text", "text": "Partial"}
            })()
            raise MockClientError("Client disconnected")

        async def get_final_message(self):
            raise MockClientError("Client disconnected")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Set up mock
    assistant.client.messages.stream.return_value = MockStream()

    # Test streaming with disconnect
    events = []
    with pytest.raises(ConnectionError) as exc_info:
        async for event in assistant.stream_response(history):
            events.append(event)

    # Verify partial events before disconnect
    assert len(events) == 2
    assert events[0].event_type == StandardEventType.MESSAGE_START
    assert events[1].event_type == StandardEventType.TEXT_TOKEN
    assert "Client disconnected" in str(exc_info.value)
