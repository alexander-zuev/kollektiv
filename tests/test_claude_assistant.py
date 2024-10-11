from unittest.mock import MagicMock, Mock, patch

import pytest
from anthropic.types.beta.prompt_caching import PromptCachingBetaUsage

from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import VectorDB


@pytest.fixture
def mock_vector_db():
    """Fixture to mock the vector database dependency."""
    return MagicMock(spec=VectorDB)


@pytest.fixture
def claude_assistant(mock_vector_db):
    """
    Fixture to create an instance of ClaudeAssistant with mocked dependencies.

    Patches:
    - anthropic.Anthropic: Mocked to prevent actual API calls.
    - tiktoken.get_encoding: Mocked encoding function.
    """
    with patch("anthropic.Anthropic") as mock_anthropic, patch("tiktoken.get_encoding") as mock_encoding:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_tokenizer = Mock()
        mock_tokenizer.encode.side_effect = lambda x: list(range(len(x)))
        mock_encoding.return_value = mock_tokenizer

        # Create a real VectorDB instance instead of a mock
        real_vector_db = VectorDB()

        assistant = ClaudeAssistant(vector_db=real_vector_db)
        assistant.client = mock_client
        return assistant


def test_streaming_response(claude_assistant):
    """
    Test the stream_response method to ensure it correctly handles streaming responses.
    """
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
    claude_assistant.client.messages.stream.return_value = mock_stream

    # Mock the conversation history to return an empty list initially
    claude_assistant.conversation_history.get_conversation_history = Mock(return_value=[])

    # Invoke the method under test
    response = list(claude_assistant.stream_response("Test input"))

    # Assertions to verify the streaming response
    assert response == [
        {"type": "text", "content": "Hello"},
        {"type": "text", "content": " world"},
    ], "Streaming response does not match expected output."

    # Verify that the stream method was called once with the correct input
    claude_assistant.client.messages.stream.assert_called_once_with(
        messages=[],
        system=claude_assistant.cached_system_prompt(),
        max_tokens=8192,
        model=claude_assistant.model_name,
        tools=claude_assistant.cached_tools(),
        extra_headers=claude_assistant.extra_headers,
    )


def test_non_streaming_response(claude_assistant):
    """
    Test the not_stream_response method to ensure it correctly handles non-streaming responses.
    """
    # Create a mock response object
    mock_response = Mock(
        content=[Mock(text="Non-streaming response")],
        stop_reason="stop",
        usage=PromptCachingBetaUsage(
            input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0
        ),
    )

    # Configure the mocked create method to return the mock_response
    claude_assistant.client.beta.prompt_caching.messages.create.return_value = mock_response

    # Mock the conversation history to return an empty list initially
    claude_assistant.conversation_history.get_conversation_history = Mock(return_value=[])

    # Invoke the method under test
    response = claude_assistant.not_stream_response("Test input")

    # Assertions to verify the non-streaming response
    assert response == "Non-streaming response", "Non-streaming response does not match expected output."

    # Verify that the create method was called once with the correct input
    claude_assistant.client.beta.prompt_caching.messages.create.assert_called_once_with(
        messages=[],
        system=claude_assistant.cached_system_prompt(),
        max_tokens=8192,
        model=claude_assistant.model_name,
        tools=claude_assistant.cached_tools(),
    )


def test_conversation_history_handling(claude_assistant):
    """
    Test the conversation history management within the assistant.
    """
    # Add messages to the conversation history
    claude_assistant.conversation_history.add_message("user", "Hello")
    claude_assistant.conversation_history.add_message("assistant", "Hi there!")
    claude_assistant.conversation_history.add_message("user", "How are you?")

    # Retrieve the conversation history
    history = claude_assistant.conversation_history.get_conversation_history()

    # Assertions to verify the conversation history
    assert len(history) == 3, "Conversation history does not contain the expected number of messages."
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"
    assert history[2]["role"] == "user"
    assert history[2]["content"] == "How are you?"
