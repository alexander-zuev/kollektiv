from unittest.mock import MagicMock, Mock, patch

import pytest
from anthropic.types.beta.prompt_caching import PromptCachingBetaUsage

from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import VectorDB


@pytest.fixture
def mock_vector_db():
    """Create a mock object for VectorDB.

    Returns:
        MagicMock: A mock object that mimics the behavior of VectorDB.
    """
    return MagicMock(spec=VectorDB)


@pytest.fixture
def real_vector_db():
    """Create a real VectorDB instance for testing.

    Returns:
        VectorDB: A real instance of VectorDB.
    """
    return VectorDB()


@pytest.fixture
def claude_assistant_with_mock(mock_vector_db):
    """Set up a ClaudeAssistant instance with mocked dependencies.

    Args:
        mock_vector_db: A mock of the VectorDB class used for testing.

    Returns:
        ClaudeAssistant: An instance of ClaudeAssistant with dependencies mocked.
    """
    with patch("anthropic.Anthropic") as mock_anthropic, patch("tiktoken.get_encoding") as mock_encoding:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_tokenizer = Mock()
        mock_tokenizer.encode.side_effect = lambda x: list(range(len(x)))
        mock_encoding.return_value = mock_tokenizer

        assistant = ClaudeAssistant(vector_db=mock_vector_db)
        assistant.client = mock_client
        return assistant


@pytest.fixture
def claude_assistant_with_real_db(real_vector_db):
    """Set up a ClaudeAssistant instance with real VectorDB.

    Args:
        real_vector_db: A real instance of VectorDB.

    Returns:
        ClaudeAssistant: An instance of ClaudeAssistant with real VectorDB.
    """
    assistant = ClaudeAssistant(vector_db=real_vector_db)
    return assistant


class TestClaudeAssistantInitialization:
    """Test module for ClaudeAssistant initialization."""

    def test_initialize_with_default_parameters(self, claude_assistant_with_real_db):
        """Tests default initialization."""
        assistant = claude_assistant_with_real_db
        assert assistant.client is not None
        assert assistant.conversation_history is not None
        assert "You are an advanced AI assistant" in assistant.system_prompt


class TestClaudeAssistantConversationHistory:
    """Test module for ClaudeAssistant conversation history handling."""

    def test_add_user_message_to_conversation_history(self, claude_assistant_with_real_db):
        """Tests adding message to conversation history."""
        assistant = claude_assistant_with_real_db
        user_message = "Hello, how are you?"
        assistant.conversation_history.add_message(role="user", content=user_message)
        history = assistant.conversation_history.get_conversation_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == user_message

    def test_conversation_history_handling(self, claude_assistant_with_mock):
        """Test the handling and retrieval of conversation history."""
        assistant = claude_assistant_with_mock

        # Add messages to the conversation history
        assistant.conversation_history.add_message("user", "Hello")
        assistant.conversation_history.add_message("assistant", "Hi there!")
        assistant.conversation_history.add_message("user", "How are you?")

        # Retrieve the conversation history
        history = assistant.conversation_history.get_conversation_history()

        # Assertions to verify the conversation history
        assert len(history) == 3, "Conversation history does not contain the expected number of messages."
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "How are you?"


class TestClaudeAssistantSystemPrompt:
    """Test module for ClaudeAssistant system prompt handling."""

    def test_update_system_prompt_with_document_summaries(self, claude_assistant_with_real_db):
        """Tests update of system prompt."""
        assistant = claude_assistant_with_real_db
        document_summaries = [{"filename": "doc1.txt", "summary": "Summary of doc1", "keywords": ["keyword1"]}]
        assistant.update_system_prompt(document_summaries)
        assert "Summary of doc1" in assistant.system_prompt

    def test_update_system_prompt_with_incomplete_document_summaries(self, claude_assistant_with_real_db):
        """Test update with incomplete document summaries."""
        assistant = claude_assistant_with_real_db
        incomplete_summaries = [{"filename": "doc1.txt", "summary": "Summary of doc1"}]  # Missing 'keywords'
        with pytest.raises(KeyError):
            assistant.update_system_prompt(incomplete_summaries)


class TestClaudeAssistantResponses:
    """Test module for ClaudeAssistant response handling."""

    def test_streaming_response(self, claude_assistant_with_mock):
        """Test the streaming response from the Claude assistant."""
        assistant = claude_assistant_with_mock

        # Create a MagicMock stream object with iterable mock messages
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.__iter__.return_value = iter(
            [Mock(type="text", text="Hello"), Mock(type="text", text=" world"), Mock(type="message_stop")]
        )

        # Set usage attributes to return integers
        final_message = Mock(content=[Mock(text="Hello world")], usage=Mock(input_tokens=10, output_tokens=5))
        mock_stream.get_final_message.return_value = final_message

        # Configure the mocked stream response
        assistant.client.messages.stream.return_value = mock_stream

        # Mock the conversation history to return an empty list initially
        assistant.conversation_history.get_conversation_history = Mock(return_value=[])

        # Invoke the method under test
        response = list(assistant.stream_response("Test input"))

        # Assertions to verify the streaming response
        assert response == [
            {"type": "text", "content": "Hello"},
            {"type": "text", "content": " world"},
        ], "Streaming response does not match expected output."

        # Verify that the stream method was called once with the correct input
        assistant.client.messages.stream.assert_called_once_with(
            messages=[],
            system=assistant.cached_system_prompt(),
            max_tokens=8192,
            model=assistant.model_name,
            tools=assistant.cached_tools(),
            extra_headers=assistant.extra_headers,
        )

    def test_non_streaming_response(self, claude_assistant_with_mock):
        """Test the non-streaming response of the Claude Assistant."""
        assistant = claude_assistant_with_mock

        # Create a mock response object
        mock_response = Mock(
            content=[Mock(text="Non-streaming response")],
            stop_reason="stop",
            usage=PromptCachingBetaUsage(
                input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0
            ),
        )

        # Configure the mocked create method to return the mock_response
        assistant.client.beta.prompt_caching.messages.create.return_value = mock_response

        # Mock the conversation history to return an empty list initially
        assistant.conversation_history.get_conversation_history = Mock(return_value=[])

        # Invoke the method under test
        response = assistant.not_stream_response("Test input")

        # Assertions to verify the non-streaming response
        assert response == "Non-streaming response", "Non-streaming response does not match expected output."

        # Verify that the create method was called once with the correct input
        assistant.client.beta.prompt_caching.messages.create.assert_called_once_with(
            messages=[],
            system=assistant.cached_system_prompt(),
            max_tokens=8192,
            model=assistant.model_name,
            tools=assistant.cached_tools(),
        )
