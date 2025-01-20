"""Unit tests for ClaudeAssistant."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import (
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    InputJSONDelta,
    MessageStreamEvent,
    RawContentBlockDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextDelta,
)

from src.core._exceptions import NonRetryableLLMError
from src.core.chat.llm_assistant import ClaudeAssistant
from src.models.chat_models import (
    AssistantMessage,
    ConversationHistory,
    ConversationMessage,
    Role,
    StreamErrorEvent,
    StreamEventType,
    TextBlock,
    TextDeltaStream,
    ToolResultBlock,
    ToolUseBlock,
)


@pytest.fixture
def basic_conversation_history(sample_uuid):
    """Fixture for a basic conversation history."""
    return ConversationHistory(
        conversation_id=sample_uuid,
        messages=[
            ConversationMessage(message_id=sample_uuid, role=Role.USER, content=[TextBlock(text="Hello, Claude")])
        ],
    )


@pytest.fixture
def tool_use_conversation(sample_uuid):
    """Fixture for a conversation history with a tool use message."""
    return ConversationHistory(
        conversation_id=sample_uuid,
        messages=[
            ConversationMessage(
                message_id=sample_uuid,
                role=Role.USER,
                content=[TextBlock(text="Please search for Python documentation")],
            )
        ],
    )


@pytest.mark.asyncio
async def test_initialization(
    mock_vector_db: MagicMock,
    mock_retriever: MagicMock,
    mock_anthropic_client: AsyncMock,
    mock_tool_manager: MagicMock,
    mock_prompt_manager: MagicMock,
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
    mock_anthropic_client.assert_called_once()


@pytest.mark.asyncio
async def test_update_system_prompt(claude_assistant_with_mocks: ClaudeAssistant, mock_prompt_manager: MagicMock):
    """Test that the system prompt is updated correctly with document summaries."""
    test_summaries = [
        {"filename": "test_doc.md", "summary": "Test document about Python", "keywords": ["python", "programming"]}
    ]
    await claude_assistant_with_mocks.update_system_prompt(test_summaries)
    mock_prompt_manager.get_system_prompt.assert_called_once()
    assert "test_doc.md" in claude_assistant_with_mocks.system_prompt.text
    assert "Test document about Python" in claude_assistant_with_mocks.system_prompt.text


@pytest.mark.asyncio
async def test_stream_response_text_only(
    claude_assistant_with_mocks: ClaudeAssistant,
    basic_conversation_history: ConversationHistory,
    mock_anthropic_client: AsyncMock,
    streaming_events: dict,
):
    """Test basic message streaming without tool use."""
    # Mock the stream to return a simple text response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text="Test response")]
    mock_stream = AsyncMock()
    mock_stream.get_final_message.return_value = mock_message

    async def mock_stream_context():
        yield mock_stream

    mock_anthropic_client.messages.stream = AsyncMock(__aenter__=mock_stream_context)

    events = []
    async for event in claude_assistant_with_mocks.stream_response(basic_conversation_history):
        events.append(event)

    # Verify event sequence
    assert any(e.event_type == StreamEventType.MESSAGE_START for e in events)
    assert any(e.event_type == StreamEventType.TEXT_TOKEN for e in events)
    assert any(e.event_type == StreamEventType.ASSISTANT_MESSAGE for e in events)
    assert any(e.event_type == StreamEventType.MESSAGE_STOP for e in events)


@pytest.mark.asyncio
async def test_stream_response_with_tool_call(
    claude_assistant_with_mocks: ClaudeAssistant,
    tool_use_conversation: ConversationHistory,
    mock_anthropic_client: AsyncMock,
):
    """Test streaming with tool use."""
    # Mock the stream to return a tool use response
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(type="tool_use", id="test-tool-id", name="rag_search", input={"rag_query": "test query"})
    ]
    mock_stream = AsyncMock()
    mock_stream.get_final_message.return_value = mock_message

    async def mock_stream_context():
        yield mock_stream

    mock_anthropic_client.messages.stream = AsyncMock(__aenter__=mock_stream_context)

    events = []
    async for event in claude_assistant_with_mocks.stream_response(tool_use_conversation):
        events.append(event)

    # Verify tool use sequence
    assert any(e.event_type == StreamEventType.MESSAGE_START for e in events)
    assert any(e.event_type == StreamEventType.TOOL_RESULT for e in events)
    tool_result = next(e for e in events if e.event_type == StreamEventType.TOOL_RESULT)
    assert isinstance(tool_result.event_data, ToolResultBlock)
    assert "Here is context retrieved by RAG search" in tool_result.event_data.content
    assert any(e.event_type == StreamEventType.ASSISTANT_MESSAGE for e in events)
    assert any(e.event_type == StreamEventType.MESSAGE_STOP for e in events)


@pytest.mark.asyncio
async def test_stream_response_error_handling(
    claude_assistant_with_mocks: ClaudeAssistant,
    basic_conversation_history: ConversationHistory,
    mock_anthropic_client: AsyncMock,
):
    """Test error handling in stream response."""
    # Simulate error in streaming
    mock_anthropic_client.messages.stream.side_effect = Exception("Test error")

    with pytest.raises(NonRetryableLLMError) as exc_info:
        async for _ in claude_assistant_with_mocks.stream_response(basic_conversation_history):
            pass

    assert "Test error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_use_rag_search(claude_assistant_with_mocks: ClaudeAssistant, mock_retriever: AsyncMock):
    """Test successful RAG tool execution."""
    tool_inputs = ToolUseBlock(
        block_type="tool_use",
        id="test-id",
        name="rag_search",
        input={"rag_query": "test query"},
    )

    result = await claude_assistant_with_mocks.use_rag_search(tool_inputs)

    mock_retriever.retrieve.assert_called_once()
    assert isinstance(result, list)
    assert "Document's relevance score" in result[0]


@pytest.mark.asyncio
async def test_generate_multi_query(claude_assistant_with_mocks: ClaudeAssistant, mock_anthropic_client: AsyncMock):
    """Test multi query generation."""
    # Mock the Anthropic API response
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(
            type="tool_use",
            input={"queries": ["query1", "query2", "query3"]},
        )
    ]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_message)

    query = "test query"
    result = await claude_assistant_with_mocks.generate_multi_query(query)

    mock_anthropic_client.messages.create.assert_called_once()
    assert isinstance(result, list)
    assert len(result) == 3
    assert "query1" in result
    assert "query2" in result
    assert "query3" in result


@pytest.mark.asyncio
async def test_parse_tool_response_invalid(
    claude_assistant_with_mocks: ClaudeAssistant, mock_anthropic_client: AsyncMock
):
    """Test handling of invalid tool responses."""
    # Mock the Anthropic API response with missing 'queries' key
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="tool_use", input={"invalid": "response"})]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_message)

    with pytest.raises(ValueError, match="Invalid tool response format"):
        await claude_assistant_with_mocks.generate_multi_query("test query")


@pytest.mark.asyncio
async def test_handle_message_start(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle message start event."""
    event = RawMessageStartEvent(
        type="message_start",
        message={
            "id": "test-message-id",
            "content": [],
            "model": "test-model",
            "role": "assistant",
            "type": "message",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    )
    result = claude_assistant_with_mocks.handle_message_start(event)
    assert result.event_type == StreamEventType.MESSAGE_START


@pytest.mark.asyncio
async def test_handle_content_block_start_tool_use(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle content block start event for tool use."""
    event = ContentBlockStartEvent(
        type="content_block_start",
        content_block=MagicMock(
            type="tool_use",
            id="test-id",
            name="test-tool",
            model_dump=lambda: {"type": "tool_use", "id": "test-id", "name": "test-tool"},
        ),
        index=0,
    )
    result = claude_assistant_with_mocks.handle_content_block_start(event)
    assert isinstance(result, ToolUseBlock)
    assert result.id == "test-id"
    assert result.name == "test-tool"


@pytest.mark.asyncio
async def test_handle_content_block_start_not_tool_use(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle content block start event when not tool use."""
    event = ContentBlockStartEvent(
        type="content_block_start",
        content_block=MagicMock(type="text", id="test-id", model_dump=lambda: {"type": "text", "id": "test-id"}),
        index=0,
    )
    result = claude_assistant_with_mocks.handle_content_block_start(event)
    assert result is None


@pytest.mark.asyncio
async def test_handle_content_block_delta_text(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle content block delta event for text."""
    event = RawContentBlockDeltaEvent(
        type="content_block_delta", delta=TextDelta(type="text_delta", text="test"), index=0
    )
    result, _ = claude_assistant_with_mocks.handle_content_block_delta(event, "")
    assert isinstance(result.data, TextDeltaStream)
    assert result.data.text == "test"
    assert result.event_type == StreamEventType.TEXT_TOKEN


@pytest.mark.asyncio
async def test_handle_content_block_delta_json(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle content block delta event for json."""
    event = RawContentBlockDeltaEvent(
        type="content_block_delta",
        delta=InputJSONDelta(type="input_json_delta", partial_json='{"key": "value"}'),
        index=0,
    )
    _, json_string = claude_assistant_with_mocks.handle_content_block_delta(event, "")
    assert json_string == '{"key": "value"}'


@pytest.mark.asyncio
async def test_handle_content_block_stop_tool_use(
    claude_assistant_with_mocks: ClaudeAssistant, mock_retriever: AsyncMock
):
    """Test handle content block stop event for tool use."""
    tool_use_block = ToolUseBlock(
        block_type="tool_use", id="test-id", name="rag_search", input={"rag_query": "test query"}
    )
    event = ContentBlockStopEvent(
        type="content_block_stop", content_block=MagicMock(type="tool_use", id="test-id"), index=0
    )
    result = await claude_assistant_with_mocks.handle_content_block_stop(
        event, tool_use_block, '{"rag_query": "test query"}'
    )
    assert isinstance(result, ToolResultBlock)
    assert "Here is context retrieved by RAG search" in result.content
    mock_retriever.retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_handle_content_block_stop_json_error(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle content block stop event with JSON parsing error."""
    tool_use_block = ToolUseBlock(
        block_type="tool_use", id="test-id", name="rag_search", input={"rag_query": "test query"}
    )
    event = ContentBlockStopEvent(
        type="content_block_stop", content_block=MagicMock(type="tool_use", id="test-id"), index=0
    )
    with pytest.raises(NonRetryableLLMError, match="Failed to parse tool input JSON from LLM response"):
        await claude_assistant_with_mocks.handle_content_block_stop(event, tool_use_block, "invalid json")


@pytest.mark.asyncio
async def test_handle_error(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle error event."""
    event = MessageStreamEvent(
        type="error",
        error="test error",
        message={
            "id": "test-message-id",
            "content": [],
            "model": "test-model",
            "role": "assistant",
            "type": "message",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    )
    result = claude_assistant_with_mocks.handle_error(event)
    assert result.event_type == StreamEventType.ERROR
    assert isinstance(result.data, StreamErrorEvent)
    assert result.data.data["error"] == "test error"


@pytest.mark.asyncio
async def test_handle_message_stop(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle message stop event."""
    event = RawMessageStopEvent(type="message_stop", message={})
    result = claude_assistant_with_mocks.handle_message_stop(event)
    assert result.event_type == StreamEventType.MESSAGE_STOP


@pytest.mark.asyncio
async def test_handle_full_message(claude_assistant_with_mocks: ClaudeAssistant):
    """Test handle full message event."""
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(type="text", text="test text", model_dump=lambda: {"type": "text", "text": "test text"}),
        MagicMock(
            type="tool_use",
            id="test-id",
            name="test-tool",
            input={"key": "value"},
            model_dump=lambda: {"type": "tool_use", "id": "test-id", "name": "test-tool", "input": {"key": "value"}},
        ),
    ]
    mock_stream = AsyncMock()
    mock_stream.get_final_message.return_value = mock_message
    result = await claude_assistant_with_mocks.handle_full_message(mock_stream)
    assert result.event_type == StreamEventType.ASSISTANT_MESSAGE
    assert isinstance(result.data, AssistantMessage)
    assert len(result.data.content) == 2
    assert isinstance(result.data.content[0], TextBlock)
    assert isinstance(result.data.content[1], ToolUseBlock)
    assert result.data.content[0].text == "test text"
    assert result.data.content[1].id == "test-id"
