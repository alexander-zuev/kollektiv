"""Unit tests for ClaudeAssistant."""
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from anthropic import (
    APIConnectionError,
    APITimeoutError,
    AsyncAnthropic,
    RateLimitError,
)
from anthropic.types import (
    Message,
    MessageStartEvent,
    MessageStopEvent,
    Usage,
)
from fastapi import WebSocketDisconnect

from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.events import StreamingError
from src.core.chat.exceptions import TokenLimitError
from src.core.chat.system_prompt import SystemPrompt
from src.core.search.vector_db import VectorDB
from src.models.chat_models import (
    ConversationMessage,
    MessageContent,
    Role,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

# Test constants
TEST_USER_MESSAGE = "Hello, how are you?"
TEST_SYSTEM_PROMPT = "You are a helpful assistant."

# Mock responses
MOCK_RESPONSE = "I'm doing well, thank you for asking!"
MOCK_ERROR_MESSAGE = "An error occurred during streaming."

# Utility functions
async def async_generator():
    """Helper function to create async generator."""
    yield "test"


@pytest.fixture
async def claude_assistant_with_mock():
    """Create a mock Claude assistant for testing."""
    # Create base mock client
    mock_client = AsyncMock()

    # Create messages mock with create method
    messages_mock = AsyncMock()
    messages_mock.create = AsyncMock()

    # Set up the mock hierarchy
    mock_client.messages = messages_mock

    # Create mock vector db
    mock_vector_db = AsyncMock(spec=VectorDB)
    mock_vector_db.search = AsyncMock(return_value=[
        {"text": "Test result 1", "score": 0.9},
        {"text": "Test result 2", "score": 0.8}
    ])

    # Create assistant with mocks
    assistant = ClaudeAssistant(
        client=mock_client,
        vector_db=mock_vector_db,
        system_prompt=SystemPrompt(TEST_SYSTEM_PROMPT),
        max_tokens=1000
    )

    return assistant


@pytest.mark.asyncio
async def test_add_message_to_conversation_history(claude_assistant_with_mock):
    """Test adding a message to conversation history."""
    assistant = await claude_assistant_with_mock

    # Add user message
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    # Verify message was added
    assert len(assistant.conversation_history.messages) == 1
    message = assistant.conversation_history.messages[0]
    assert message.role == Role.USER
    assert message.content.blocks[0].text == TEST_USER_MESSAGE


@pytest.mark.asyncio
async def test_update_system_prompt(claude_assistant_with_mock):
    """Test updating system prompt."""
    assistant = await claude_assistant_with_mock
    await assistant.update_system_prompt(TEST_SYSTEM_PROMPT)
    assert assistant.system_prompt.content == TEST_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_get_response(claude_assistant_with_mock):
    """Test getting a response from Claude."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock response
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=[
        MessageStartEvent(
            type="message_start",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20)
            )
        ),
        Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[{"type": "text", "text": "Test response"}],
            model="claude-3-opus-20240229",
            usage=Usage(input_tokens=10, output_tokens=20)
        ),
        MessageStopEvent(
            type="message_stop",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[{"type": "text", "text": "Test response"}],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20)
            )
        ),
        StopAsyncIteration
    ])
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message and get response
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    response = await assistant.get_response(assistant.conversation_history)
    assert isinstance(response, ConversationMessage)
    assert response.role == Role.ASSISTANT
    assert len(response.content.blocks) == 1
    assert isinstance(response.content.blocks[0], TextBlock)
    assert response.content.blocks[0].text == "Test response"


@pytest.mark.asyncio
async def test_handle_tool_use_rag_search(claude_assistant_with_mock):
    """Test handling tool use for RAG search."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client
    mock_vector_db = assistant.vector_db

    # Setup mock search results
    mock_vector_db.search.return_value = ["Test document"]

    # Setup mock stream
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)

    # Create a sequence of events for the stream
    events = [
        MessageStartEvent(
            type="message_start",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20)
            )
        ),
        Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[{
                "type": "tool_use",
                "tool": {
                    "name": "rag_search",
                    "arguments": {"query": "test query"}
                }
            }],
            model="claude-3-opus-20240229",
            usage=Usage(input_tokens=10, output_tokens=20)
        ),
        MessageStopEvent(
            type="message_stop",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[{
                    "type": "tool_use",
                    "tool": {
                        "name": "rag_search",
                        "arguments": {"query": "test query"}
                    }
                }],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20)
            )
        )
    ]

    mock_stream.__anext__.side_effect = events
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text="What documents do you have?")])
    )

    response = await assistant.get_response(assistant.conversation_history)
    assert isinstance(response, ConversationMessage)
    assert isinstance(response.content.blocks[0], ToolUseBlock)
    assert response.content.blocks[0].name == "rag_search"


@pytest.mark.asyncio
async def test_stream_response_token_limit_error(claude_assistant_with_mock):
    """Test token limit error handling in streaming."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream to raise token limit error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=TokenLimitError("Token limit exceeded"))
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    # Test token limit error handling
    with pytest.raises(StreamingError) as exc_info:
        async for _ in assistant.stream_response(assistant.conversation_history):
            pass

    assert "Token limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_connection_error(claude_assistant_with_mock):
    """Test connection error handling in streaming."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises connection error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=APIConnectionError(
        request={"method": "POST", "url": "https://api.anthropic.com/v1/messages"},
        response=None,
        body={"error": {"type": "connection_error", "message": "Connection failed"}}
    ))
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message and attempt to stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    with pytest.raises(StreamingError):
        async for _ in assistant.stream_response(assistant.conversation_history):
            pass


@pytest.mark.asyncio
async def test_stream_response_retryable_error(claude_assistant_with_mock):
    """Test retryable error handling in streaming."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream to raise rate limit error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    # Test rate limit error handling
    with pytest.raises(StreamingError) as exc_info:
        async for _ in assistant.stream_response(assistant.conversation_history):
            pass

    assert "Rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response_successful_flow(claude_assistant_with_mock):
    """Test successful streaming flow."""
    assistant = claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream events
    message = Message(
        id="msg_123",
        type="message",
        role="assistant",
        content=[],
        model="claude-3-opus-20240229",
        usage=Usage(input_tokens=10, output_tokens=20)
    )

    events = [
        MessageStartEvent(
            message_id="msg_123",
            model="claude-3-opus-20240229"
        ),
        Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[{"type": "text", "text": "Hello"}],
            model="claude-3-opus-20240229",
            usage=Usage(input_tokens=10, output_tokens=20)
        ),
        Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[{"type": "text", "text": ", how can I help?"}],
            model="claude-3-opus-20240229",
            usage=Usage(input_tokens=10, output_tokens=20)
        ),
        MessageStopEvent(
            message_id="msg_123",
            end_reason="stop_sequence",
            model="claude-3-opus-20240229",
            usage={"input_tokens": 10, "output_tokens": 20}
        )
    ]

    # Setup mock stream
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=events + [StopAsyncIteration])
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message and stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    collected_text = ""
    async for event in assistant.stream_response(assistant.conversation_history):
        if isinstance(event, Message) and event.content:
            collected_text += event.content[0]["text"]

    assert collected_text == "Hello, how can I help?"
    assert len(assistant.conversation_history.messages) == 1


@pytest.mark.asyncio
async def test_stream_response_client_disconnect(claude_assistant_with_mock):
    """Test client disconnect handling in streaming."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises client disconnect error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=WebSocketDisconnect())
    mock_client.messages.create = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER,
        content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    # Test client disconnect error
    with pytest.raises(StreamingError):
        async for _ in assistant.stream_response(assistant.conversation_history):
            pass
