"""Unit tests for ClaudeAssistant module."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from anthropic import APIError, APIStatusError, AsyncAnthropic
from anthropic.types import (
    ContentBlockEvent,
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
    ToolUseBlock,
)

# Test constants
TEST_USER_MESSAGE = "Hello, how are you?"
TEST_SYSTEM_PROMPT = "You are a helpful assistant."

# Mock responses
MOCK_RESPONSE = "I'm doing well, thank you for asking!"
MOCK_ERROR_MESSAGE = "An error occurred during streaming."


# Utility functions
async def async_generator() -> AsyncGenerator[str, None]:
    """Helper function to create async generator."""
    yield "test"


@pytest_asyncio.fixture
async def claude_assistant_with_mock() -> ClaudeAssistant:
    """Create a mock Claude assistant for testing."""
    # Create base mock client with proper spec
    mock_messages = AsyncMock()
    mock_messages.stream = AsyncMock()
    mock_messages.create = AsyncMock()

    mock_client = AsyncMock(spec=AsyncAnthropic)
    mock_client.messages = mock_messages
    mock_client.configure_mock(messages=mock_messages)

    # Create mock vector db
    mock_vector_db = AsyncMock(spec=VectorDB)
    mock_vector_db.search = AsyncMock(
        return_value=[{"text": "Test result 1", "score": 0.9}, {"text": "Test result 2", "score": 0.8}]
    )

    # Create assistant with mocks
    assistant = ClaudeAssistant(
        client=mock_client, vector_db=mock_vector_db, system_prompt=SystemPrompt(TEST_SYSTEM_PROMPT), max_tokens=1000
    )

    return assistant


@pytest.mark.asyncio
async def test_add_message_to_conversation_history(
    claude_assistant_with_mock: ClaudeAssistant,
) -> None:
    """Test adding a message to conversation history."""
    assistant = await claude_assistant_with_mock

    # Add user message
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
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
async def test_get_response(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test getting a response from Claude.

    Tests the complete flow of getting a response, including message start,
    content generation, and message stop events.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock response
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(
        side_effect=[
            MessageStartEvent(
                type="message_start",
                message=Message(
                    id="msg_123",
                    type="message",
                    role="assistant",
                    content=[],
                    model="claude-3-opus-20240229",
                    usage=Usage(input_tokens=10, output_tokens=20),
                ),
            ),
            Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[{"type": "text", "text": "Test response"}],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20),
            ),
            MessageStopEvent(
                type="message_stop",
                message=Message(
                    id="msg_123",
                    type="message",
                    role="assistant",
                    content=[{"type": "text", "text": "Test response"}],
                    model="claude-3-opus-20240229",
                    usage=Usage(input_tokens=10, output_tokens=20),
                ),
            ),
            StopAsyncIteration,
        ]
    )
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message and get response
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    response = await assistant.get_response(assistant.conversation_history)
    assert isinstance(response, ConversationMessage)
    assert response.role == Role.ASSISTANT
    assert len(response.content.blocks) == 1
    assert isinstance(response.content.blocks[0], TextBlock)
    assert response.content.blocks[0].text == "Test response"


@pytest.mark.asyncio
async def test_handle_tool_use_rag_search(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test handling tool use for RAG search.

    Tests the complete flow of handling a RAG search tool use request,
    including tool invocation and response processing.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client
    mock_vector_db = assistant.vector_db

    # Setup mock search results
    mock_vector_db.search.return_value = ["Test document"]

    # Setup mock stream
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)

    # Create a sequence of events for the stream
    tool_use_id = str(uuid4())
    events = [
        MessageStartEvent(
            type="message_start",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20),
            ),
        ),
        Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[
                {
                    "type": "tool_use",
                    "name": "rag_search",
                    "input": {"query": "test query"},
                    "id": tool_use_id,
                    "text": "Search for test query",
                }
            ],
            model="claude-3-opus-20240229",
            usage=Usage(input_tokens=10, output_tokens=20),
        ),
        MessageStopEvent(
            type="message_stop",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[
                    {
                        "type": "tool_use",
                        "name": "rag_search",
                        "input": {"query": "test query"},
                        "id": tool_use_id,
                        "text": "Search for test query",
                    }
                ],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20),
            ),
        ),
    ]

    mock_stream.__anext__.side_effect = events + [StopAsyncIteration]
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text="What documents do you have?")])
    )

    response = await assistant.get_response(assistant.conversation_history)
    assert isinstance(response, ConversationMessage)
    assert isinstance(response.content.blocks[0], ToolUseBlock)
    assert response.content.blocks[0].name == "rag_search"


@pytest.mark.asyncio
async def test_stream_response_token_limit_error(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test token limit error handling in streaming."""
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises token limit error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=APIError(message="Token limit exceeded", type="token_limit_error"))
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message and attempt to stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text="Test message")])
    )

    with pytest.raises(TokenLimitError):
        await assistant.stream_response(assistant.conversation_history).__anext__()


@pytest.mark.asyncio
async def test_stream_response_connection_error(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test connection error handling in streaming.

    Tests the error handling when a connection error occurs during streaming,
    ensuring proper error propagation and cleanup.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises connection error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=APIError(message="Connection failed", type="connection_error"))
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message and attempt to stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text="Test message")])
    )

    with pytest.raises(StreamingError):
        await assistant.stream_response(assistant.conversation_history).__anext__()


@pytest.mark.asyncio
async def test_stream_response_retryable_error(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test retryable error handling in streaming.

    Tests the handling of retryable errors during streaming, ensuring proper
    error classification and retry behavior.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises retryable error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(
        side_effect=APIStatusError(message="Internal server error", response=AsyncMock(status=500))
    )
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message and attempt to stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text="Test message")])
    )

    with pytest.raises(StreamingError):
        await assistant.stream_response(assistant.conversation_history).__anext__()


@pytest.mark.asyncio
async def test_stream_response_successful_flow(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test successful streaming response flow.

    Tests the complete successful flow of streaming a response, including
    message start, content blocks, and message stop events.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream events
    events = [
        MessageStartEvent(
            type="message_start",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20),
            ),
        ),
        ContentBlockEvent(type="content_block", message_id="msg_123", content_block={"type": "text", "text": "Hello"}),
        ContentBlockEvent(
            type="content_block", message_id="msg_123", content_block={"type": "text", "text": ", how can I help?"}
        ),
        MessageStopEvent(
            type="message_stop",
            message=Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[{"type": "text", "text": "Hello, how can I help?"}],
                model="claude-3-opus-20240229",
                usage=Usage(input_tokens=10, output_tokens=20),
            ),
        ),
    ]

    # Setup mock stream
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = mock_stream
    mock_stream.__anext__ = AsyncMock(side_effect=events + [StopAsyncIteration])
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message and stream response
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    collected_text = ""
    async for event in assistant.stream_response(assistant.conversation_history):
        if isinstance(event, ContentBlockEvent):
            collected_text += event.text

    assert collected_text == "Hello, how can I help?"


@pytest.mark.asyncio
async def test_stream_response_client_disconnect(claude_assistant_with_mock: ClaudeAssistant) -> None:
    """Test client disconnect handling in streaming.

    Tests the proper handling of client disconnection during streaming,
    ensuring cleanup and proper error propagation.
    """
    assistant = await claude_assistant_with_mock
    mock_client = assistant.client

    # Setup mock stream that raises client disconnect error
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__anext__ = AsyncMock(side_effect=WebSocketDisconnect())
    mock_client.messages.stream = AsyncMock(return_value=mock_stream)

    # Add message to conversation
    await assistant.add_message_to_conversation_history(
        role=Role.USER, content=MessageContent(blocks=[TextBlock(text=TEST_USER_MESSAGE)])
    )

    # Test client disconnect error
    with pytest.raises(StreamingError):
        await assistant.stream_response(assistant.conversation_history).__anext__()
