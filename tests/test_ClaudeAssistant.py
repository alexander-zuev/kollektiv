import pytest

from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import VectorDB


class TestClaudeAssistant:
    """Test module for ClaudeAssistant."""

    # Initialize ClaudeAssistant with default parameters and verify successful setup
    def test_initialize_with_default_parameters(self):
        """Tests default init."""
        vector_db = VectorDB()
        assistant = ClaudeAssistant(vector_db=vector_db)
        assert assistant.client is not None
        assert assistant.conversation_history is not None
        assert "You are an advanced AI assistant" in assistant.system_prompt

    # Add a user message and verify it is correctly added to conversation history
    def test_add_user_message_to_conversation_history(self):
        """Tests adding message to conversation history."""
        vector_db = VectorDB()
        assistant = ClaudeAssistant(vector_db=vector_db)
        user_message = "Hello, how are you?"
        assistant.conversation_history.add_message(role="user", content=user_message)
        history = assistant.conversation_history.get_conversation_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == user_message

    # Update system prompt with document summaries and verify the prompt is updated
    def test_update_system_prompt_with_document_summaries(self):
        """Tests update of system prompt."""
        vector_db = VectorDB()
        assistant = ClaudeAssistant(vector_db=vector_db)
        document_summaries = [{"filename": "doc1.txt", "summary": "Summary of doc1", "keywords": ["keyword1"]}]
        assistant.update_system_prompt(document_summaries)
        assert "Summary of doc1" in assistant.system_prompt

    # Update system prompt with incomplete document summaries and verify error handling
    def test_update_system_prompt_with_incomplete_document_summaries(self):
        """Test update with incomplete document summaries."""
        vector_db = VectorDB()
        assistant = ClaudeAssistant(vector_db=vector_db)
        incomplete_summaries = [{"filename": "doc1.txt", "summary": "Summary of doc1"}]  # Missing 'keywords'
        with pytest.raises(KeyError):
            assistant.update_system_prompt(incomplete_summaries)
