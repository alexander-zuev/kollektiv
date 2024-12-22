"""Unit tests for ClaudeAssistant."""

import pytest

from src.core.chat.llm_assistant import ClaudeAssistant
from src.core.chat.models import StreamingEventType, ToolResultBlock
from src.exceptions.llm_exceptions import NonRetryableLLMError
from src.models.chat_models import ToolUseBlock


@pytest.mark.asyncio
async def test_initialization_with_dependencies(
    mock_vector_db,
    mock_retriever,
    mock_anthropic_client,
    mock_tool_manager,
    mock_prompt_manager,
):
    """Test successful initialization with all dependencies."""
    assistant = ClaudeAssistant(
        vector_db=mock_vector_db,
        retriever=mock_retriever,
        api_key="test-key",
        model_name="test-model",
    )
    assistant.tool_manager = mock_tool_manager
    assistant.prompt_manager = mock_prompt_manager

    assert assistant.client is not None
    assert assistant.vector_db == mock_vector_db
    assert assistant.retriever == mock_retriever
    assert len(assistant.tools) == 1
    assert assistant.tools[0].name == "rag_search"


@pytest.mark.asyncio
async def test_stream_response_basic_flow(claude_assistant_with_mocks, basic_conversation_history):
    """Test basic message streaming without tool use."""
    events = []
    async for event in claude_assistant_with_mocks.stream_response(basic_conversation_history):
        events.append(event)

    # Verify event sequence
    assert any(e.event_type == StreamingEventType.MESSAGE_START for e in events)
    assert any(e.event_type == StreamingEventType.TEXT_TOKEN for e in events)
    assert any(e.event_type == StreamingEventType.MESSAGE_STOP for e in events)


@pytest.mark.asyncio
async def test_stream_response_with_tool_use(claude_assistant_with_mocks, tool_use_conversation):
    """Test streaming with tool use."""
    events = []
    async for event in claude_assistant_with_mocks.stream_response(tool_use_conversation):
        events.append(event)

    # Verify tool use sequence
    assert any(e.event_type == StreamingEventType.TOOL_RESULT for e in events)
    tool_result = next(e for e in events if e.event_type == StreamingEventType.TOOL_RESULT)
    assert isinstance(tool_result.event_data, ToolResultBlock)
    assert "Test search result" in tool_result.event_data.content


@pytest.mark.asyncio
async def test_stream_response_error_handling(claude_assistant_with_mocks, basic_conversation_history):
    """Test error handling in stream response."""
    # Simulate error in streaming
    claude_assistant_with_mocks.client.messages.stream.side_effect = Exception("Test error")

    with pytest.raises(NonRetryableLLMError) as exc_info:
        async for _ in claude_assistant_with_mocks.stream_response(basic_conversation_history):
            pass

    assert "Test error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_tool_call_rag_search(claude_assistant_with_mocks):
    """Test successful RAG tool execution."""
    tool_inputs = ToolUseBlock(
        block_type="tool_use",
        id="test-id",
        name="rag_search",
        input={"important_context": "test query"},
    )

    result = await claude_assistant_with_mocks.handle_tool_call(tool_inputs)

    assert isinstance(result, ToolResultBlock)
    assert result.tool_use_id == "test-id"
    assert "Test search result" in result.content


@pytest.mark.asyncio
async def test_handle_tool_call_error(claude_assistant_with_mocks):
    """Test error handling in tool execution."""
    # Unknown tool
    tool_inputs = ToolUseBlock(
        block_type="tool_use",
        id="test-id",
        name="unknown_tool",
        input={},
    )

    with pytest.raises(NonRetryableLLMError) as exc_info:
        await claude_assistant_with_mocks.handle_tool_call(tool_inputs)

    assert "Unknown tool" in str(exc_info.value)
