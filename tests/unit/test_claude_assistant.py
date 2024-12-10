"""Unit tests for ClaudeAssistant."""
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import aiohttp
from anthropic import (
    APIError,
    AsyncAnthropic,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from anthropic.types import (
    ContentBlock,
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    Message,
    MessageStartEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    TextBlock,
    TextDelta,
    Usage,
)

from src.core._exceptions import (
    ClientDisconnectError,
    RetryableError,
    StreamingError,
    TokenLimitError,
)
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.events import (
    ChatEvent,
    ContentBlockEvent,
    ErrorEvent,
    MessageStartEvent,
    MessageEndEvent,
)
from src.core.search.vector_db import ResultRetriever, VectorDB
from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    MessageContent,
    Role,
    TextBlock as ChatTextBlock,
)

# Test data
TEST_SYSTEM_PROMPT = "You are a helpful assistant."
TEST_USER_MESSAGE = "Hello, how are you?"


@pytest.fixture
async def claude_assistant_with_mock():
    """Create a mock Claude assistant."""
    mock_client = AsyncMock(spec=AsyncAnthropic)
    mock_messages = AsyncMock()

    # Create a proper async context manager mock
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = AsyncMock()

    # Set up the messages.stream method to return the mock_stream
    mock_messages.stream = AsyncMock(return_value=mock_stream)
    mock_client.messages = mock_messages

    mock_vector_db = MagicMock(spec=VectorDB)
    return ClaudeAssistant(client=mock_client, vector_db=mock_vector_db)


@pytest.mark.asyncio
async def test_add_message_to_conversation_history(claude_assistant_with_mock):
    """Test adding messages to conversation history."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()

    # Add user message
    user_message = "Test message"
    conversation.append(Role.USER, user_message)

    # Verify message was added correctly
    assert len(conversation.messages) == 1
    assert conversation.messages[0].role == Role.USER
    assert isinstance(conversation.messages[0].content, MessageContent)
    assert len(conversation.messages[0].content.blocks) == 1
    assert conversation.messages[0].content.blocks[0].text == user_message


@pytest.mark.asyncio
async def test_update_system_prompt(claude_assistant_with_mock):
    """Test updating the system prompt with document summaries."""
    assistant = claude_assistant_with_mock
    summaries = [{"filename": "doc1", "summary": "Summary 1", "keywords": ["key1", "key2"]}]
    await assistant.update_system_prompt(summaries)
    assert "doc1" in assistant.system_prompt.blocks[0].text


@pytest.mark.asyncio
async def test_get_response(claude_assistant_with_mock):
    """Test getting a response from the assistant."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock successful response
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    events = [
        {"type": "message_start", "message": {"id": "msg_123", "model": "claude-3-opus-20240229"}},
        {"type": "content_block_start", "content_block": {"id": "block_1", "type": "text"}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Test", "id": "block_1"}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " response", "id": "block_1"}},
        {"type": "message_stop", "message": {
            "id": "msg_123",
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }}
    ]

    async def mock_events():
        for event in events:
            yield event

    mock_stream.__aiter__ = mock_events
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    response = await assistant.get_response(conversation)
    assert response == "Test response"
    assert len(conversation.messages) == 2  # User message + assistant response
    assert conversation.messages[-1].role == Role.ASSISTANT
    assert conversation.messages[-1].content.text == "Test response"


@pytest.mark.asyncio
async def test_handle_tool_use_rag_search(claude_assistant_with_mock):
    """Test RAG search tool usage."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock tool use response
    tool_use_id = str(uuid.uuid4())
    tool_input = {"query": "test query"}

    # Mock search results
    search_results = ["Test search results"]
    assistant.vector_db.search = AsyncMock(return_value=search_results)

    # Test tool use handling
    result = await assistant.handle_tool_use(
        tool_name="rag_search",
        tool_input=tool_input,
        tool_use_id=tool_use_id
    )

    # Verify result structure
    assert isinstance(result, dict)
    assert result["role"] == "user"
    assert isinstance(result["content"], list)
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "tool_result"
    assert result["content"][0]["tool_use_id"] == tool_use_id
    assert result["content"][0]["content"] == search_results[0]

    # Verify vector_db.search was called correctly
    assistant.vector_db.search.assert_called_once_with(query="test query")


@pytest.mark.asyncio
async def test_stream_response_token_limit_error(claude_assistant_with_mock):
    """Test token limit error handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock token limit error
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = AsyncMock(side_effect=APIStatusError(
        message="Token limit exceeded",
        response=None,
        body={"error": {"type": "rate_limit_error"}},
        type="rate_limit_error"
    ))
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    with pytest.raises(TokenLimitError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass
    assert "Token limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_connection_error(claude_assistant_with_mock):
    """Test connection error handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock connection error
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    with pytest.raises(StreamingError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass
    assert "Connection error during streaming" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_retryable_error(claude_assistant_with_mock):
    """Test retryable error handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock retryable error
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = AsyncMock(side_effect=APIStatusError(
        message="Internal server error",
        response=None,
        body={"error": {"type": "internal_server_error"}},
        type="internal_server_error"
    ))
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    with pytest.raises(StreamingError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass
    assert "API error during streaming" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_successful_flow(claude_assistant_with_mock):
    """Test successful streaming flow."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock successful streaming response
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    events = [
        {"type": "message_start", "message": {"id": "msg_123", "model": "claude-3-opus-20240229"}},
        {"type": "content_block_start", "content_block": {"id": "block_1", "type": "text"}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Test", "id": "block_1"}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " response", "id": "block_1"}},
        {"type": "message_stop", "message": {
            "id": "msg_123",
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }}
    ]

    async def mock_events():
        for event in events:
            yield event

    mock_stream.__aiter__ = mock_events
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    received_events = []
    async for event in assistant.stream_response(conversation):
        received_events.append(event)

    assert len(received_events) == 4  # message_start, 2 content_blocks, message_stop
    assert isinstance(received_events[0], MessageStartEvent)
    assert isinstance(received_events[-1], MessageEndEvent)


@pytest.mark.asyncio
async def test_stream_response_client_disconnect(claude_assistant_with_mock):
    """Test client disconnect handling in streaming."""
    assistant = claude_assistant_with_mock
    conversation = ConversationHistory()
    conversation.append(Role.USER, "Test message")

    # Mock client disconnect
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = AsyncMock(side_effect=ClientDisconnectError("Client disconnected"))
    assistant.client.messages.stream = AsyncMock(return_value=mock_stream)

    with pytest.raises(ClientDisconnectError) as exc_info:
        async for _ in assistant.stream_response(conversation):
            pass
    assert "Client disconnected" in str(exc_info.value)
