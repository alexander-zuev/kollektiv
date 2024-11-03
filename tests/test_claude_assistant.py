from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.chat.claude_assistant import ClaudeAssistant, ConversationMessage
from src.core.search.vector_db import VectorDB


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
    """Set up a ClaudeAssistant instance with mocked dependencies."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = Mock()
        # Mock handle_tool_use to return a synchronous dict instead of AsyncMock
        mock_client.handle_tool_use = Mock(
            return_value={"role": "user", "content": [{"type": "tool_result", "content": "Tool response"}]}
        )
        mock_anthropic.return_value = mock_client

        assistant = ClaudeAssistant(vector_db=mock_vector_db)
        assistant.client = mock_client

        # Create proper ConversationMessage objects
        assistant.conversation_history.messages = [ConversationMessage(role="user", content="Initial message")]
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


@pytest.fixture
def mock_get_recent_context():
    """Mock the get_recent_context method."""
    with patch("src.generation.claude_assistant.ClaudeAssistant.get_recent_context") as mock:
        mock.return_value = [{"role": "user", "content": "test query"}]
        yield mock
