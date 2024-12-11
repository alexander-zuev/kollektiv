"""Integration tests for ClaudeAssistant."""
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import ToolUseBlock

from src.core._exceptions import StreamingError
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.events import StandardEvent, StandardEventType
from src.core.search.vector_db import ResultRetriever, VectorDB
from src.models.chat_models import MessageContent, TextBlock, Role
from tests.conftest import MockEmbeddingFunction


@pytest.fixture
async def test_claude_assistant() -> ClaudeAssistant:
    """Create a test instance of ClaudeAssistant with mocked dependencies."""
    # Create mock Anthropic client
    mock_client = AsyncMock()
    mock_stream = AsyncMock()

    # Set up mock stream with proper async iterator
    async def event_generator():
        events = [
            MagicMock(
                type="message_start",
                message=MagicMock(id="msg_123", model="claude-3-sonnet-20240229")
            ),
            MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text="Test response", id="block_123"),
                message=MagicMock(id="msg_123")
            ),
            MagicMock(
                type="message_stop",
                message=MagicMock(
                    id="msg_123",
                    model="claude-3-sonnet-20240229",
                    stop_reason="end_turn",
                    usage=MagicMock(input_tokens=10, output_tokens=5)
                )
            )
        ]
        for event in events:
            yield event

    mock_stream.__aiter__.return_value = event_generator()
    mock_stream.__aenter__.return_value = mock_stream
    mock_stream.__aexit__.return_value = None
    mock_client.messages.stream.return_value = mock_stream

    # Create mock ResultRetriever with required arguments
    mock_retriever = MagicMock(spec=ResultRetriever)
    mock_retriever.collection_name = "test_collection"
    mock_retriever.embedding_function = MockEmbeddingFunction()
    mock_retriever.get_results = AsyncMock(return_value=[{"text": "Test result", "score": 0.9}])

    # Create VectorDB with mock retriever
    vector_db = VectorDB(
        embedding_function="text-embedding-3-small",
        openai_api_key="test-key"
    )
    vector_db.result_retriever = mock_retriever

    # Create test assistant
    assistant = ClaudeAssistant(
        client=mock_client,
        vector_db=vector_db,
        system_prompt="You are a helpful AI assistant.",
        model="claude-3-sonnet-20240229",
        max_tokens=4096
    )

    yield assistant

    # Cleanup after test
    await vector_db.reset_database()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_conversation_flow(test_claude_assistant: ClaudeAssistant):
    """Test the complete conversation flow with tool use."""
    print(f"\nAssistant client type: {type(test_claude_assistant.client)}")
    print(f"Vector DB type: {type(test_claude_assistant.vector_db)}")
    print(f"Is client mocked: {isinstance(test_claude_assistant.client, MagicMock)}")

    # 1. Verify empty initial state
    assert len(test_claude_assistant.conversation_history.messages) == 0

    # 2. Send initial user message
    user_query = "What do the docs say about Python?"
    test_claude_assistant.conversation_history.append(
        role=Role.USER,
        content=MessageContent(blocks=[
            {"type": "text", "text": user_query}
        ])
    )

    # 3. Simulate Claude's tool use response
    tool_use_block = ToolUseBlock(
        id="toolu_01A09q90qw90lq917835lq9",
        type="tool_use",
        name="rag_search",
        input={"query": user_query}
    )

    # 4. Handle tool use and get tool result
    tool_result = await test_claude_assistant.handle_tool_use(
        tool_name=tool_use_block.name,
        tool_input=tool_use_block.input,
        tool_use_id=tool_use_block.id
    )

    # Debug print
    print(f"Tool result: {tool_result}")
    print(f"Tool result type: {type(tool_result)}")
    print(f"Tool result role: {tool_result.get('role')}")

    # Verify tool result matches implementation
    assert isinstance(tool_result, dict)
    assert tool_result["role"] == "user"
    assert isinstance(tool_result["content"], list)
    assert len(tool_result["content"]) == 1
    assert tool_result["content"][0]["type"] == "tool_result"
    assert tool_result["content"][0]["tool_use_id"] == tool_use_block.id
    assert isinstance(tool_result["content"][0]["content"], str)

    # 5. Verify conversation history has correct sequence
    history = test_claude_assistant.conversation_history.messages
    assert len(history) == 1  # Only initial message, tool result not added to history

    # Initial user message
    assert history[0].role == Role.USER
    assert isinstance(history[0].content, MessageContent)
    assert history[0].content.blocks[0].text == user_query


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_prompt_update_and_cache(test_claude_assistant: ClaudeAssistant):
    """Test system prompt update and caching."""
    # Initial system prompt should be set from fixture
    assert test_claude_assistant.system_prompt is not None
    assert "You are a helpful AI assistant" in test_claude_assistant.system_prompt.to_anthropic()

    # Update system prompt with document summaries
    test_summaries = [
        {"filename": "test.txt", "summary": "Test document content"}
    ]
    await test_claude_assistant.update_system_prompt(test_summaries)

    # Verify prompt is updated and contains document summary
    assert test_claude_assistant.system_prompt is not None
    assert "test.txt: Test document content" in test_claude_assistant.system_prompt.to_anthropic()

    # Update with empty document summaries
    await test_claude_assistant.update_system_prompt([])
    assert test_claude_assistant.system_prompt is not None
    assert "No documents loaded" in test_claude_assistant.system_prompt.to_anthropic()

    # Reset system prompt
    test_claude_assistant.system_prompt = None
    assert test_claude_assistant.system_prompt is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handle_tool_use_error(test_claude_assistant: ClaudeAssistant):
    """Test error handling in tool use."""
    # Test with invalid tool name
    with pytest.raises(StreamingError, match="Error during tool use: Unknown tool: invalid_tool"):
        await test_claude_assistant.handle_tool_use(
            tool_name="invalid_tool",
            tool_input={"query": "test"},
            tool_use_id="test_id"
        )

    # Test with invalid input
    with pytest.raises(StreamingError, match="Error during tool use"):
        await test_claude_assistant.handle_tool_use(
            tool_name="rag_search",
            tool_input={},  # Missing required query parameter
            tool_use_id="test_id"
        )
