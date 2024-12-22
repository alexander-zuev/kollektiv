from unittest.mock import Mock, patch

from src.models.chat_models import ConversationHistory


def test_claude_assistant_initialization(claude_assistant_with_mock):
    """Test that ClaudeAssistant initializes correctly with mocked dependencies."""
    assistant = claude_assistant_with_mock
    assert assistant.client is not None
    assert isinstance(assistant.conversation_history, ConversationHistory)


async def test_add_message_to_conversation_history(claude_assistant_with_mock):
    """Test adding a message to the conversation history."""
    assistant = claude_assistant_with_mock
    initial_count = len(assistant.conversation_history.messages)
    await assistant.conversation_history.add_message(role="user", content="New message")
    assert len(assistant.conversation_history.messages) == initial_count + 1


def test_update_system_prompt(claude_assistant_with_mock):
    """Test updating the system prompt with document summaries."""
    assistant = claude_assistant_with_mock
    summaries = [{"filename": "doc1", "summary": "Summary 1", "keywords": ["key1", "key2"]}]
    assistant.update_system_prompt(summaries)
    assert "doc1" in assistant.system_prompt


def test_get_response(claude_assistant_with_mock):
    """Test generating a response from the assistant."""
    assistant = claude_assistant_with_mock

    # Configure the mock to return realistic values for input and output tokens
    mock_response = Mock()
    mock_response.usage.input_tokens = 2095
    mock_response.usage.output_tokens = 503

    # Create a mock content object with dot notation access
    content_item = Mock()
    content_item.text = "Hi! My name is Claude."
    content_item.type = "text"
    mock_response.content = [content_item]
    mock_response.stop_reason = "end_turn"

    # Mock the create method to return the mock response
    assistant.client.beta.prompt_caching.messages.create.return_value = mock_response

    response = assistant.get_response("Hello", stream=False)
    assert isinstance(response, str)
    assert response == "Hi! My name is Claude."


def test_handle_tool_use_rag_search(claude_assistant_with_mock):
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
