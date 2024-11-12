import asyncio
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from anthropic.types import ToolUseBlock

from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.search.vector_db import Reranker, ResultRetriever, VectorDB


@pytest.fixture(scope="function")
def test_claude_assistant(real_vector_db: VectorDB) -> Generator[ClaudeAssistant, None, None]:
    """Create a Claude Assistant instance with real vector DB."""
    # Create and initialize the retriever
    reranker = Reranker()
    retriever = ResultRetriever(vector_db=real_vector_db, reranker=reranker)

    # Initialize assistant with the properly set up retriever
    assistant = ClaudeAssistant(vector_db=real_vector_db)
    assistant.retriever = retriever

    # Mock the summary manager
    with patch("src.core.search.vector_db.SummaryManager") as mock_summary_manager:
        # Configure mock
        mock_instance = mock_summary_manager.return_value
        mock_instance.process_file.return_value = None
        real_vector_db.summary_manager = mock_instance

        try:
            # Add test documents (now with mocked summary manager)
            test_docs = [
                {
                    "chunk_id": "test1",
                    "data": {"text": "Python is a high-level programming language.", "headers": {"title": "Python"}},
                    "metadata": {"source_url": "test_url", "page_title": "Python Docs"},
                }
            ]
            asyncio.run(real_vector_db.add_documents(test_docs, "test.json"))
            yield assistant
        finally:
            # Clean up
            real_vector_db.reset_database()
            assistant.reset_conversation()


@pytest.mark.integration
def test_complete_conversation_flow(test_claude_assistant: ClaudeAssistant):
    """Test the complete conversation flow with tool use."""
    print(f"\nAssistant client type: {type(test_claude_assistant.client)}")
    print(f"Vector DB type: {type(test_claude_assistant.vector_db)}")
    print(f"Is client mocked: {isinstance(test_claude_assistant.client, Mock)}")

    # 1. Verify empty initial state
    assert len(test_claude_assistant.conversation_history.messages) == 0

    # 2. Send initial user message
    user_query = "What do the docs say about Python?"
    test_claude_assistant.conversation_history.add_message(role="user", content=user_query)

    # 3. Simulate Claude's tool use response
    tool_use_block = ToolUseBlock(
        id="toolu_01A09q90qw90lq917835lq9", type="tool_use", name="rag_search", input={"important_context": user_query}
    )

    # 4. Handle tool use and get tool result
    tool_result = test_claude_assistant.handle_tool_use(
        tool_name=tool_use_block.name, tool_input=tool_use_block.input, tool_use_id=tool_use_block.id
    )

    # Debug print
    print(f"Tool result: {tool_result}")  # Let's see what we actually get
    print(f"Tool result type: {type(tool_result)}")
    print(f"Tool result role: {tool_result.get('role')}")

    # Verify tool result matches implementation
    assert isinstance(tool_result, dict)

    if "error" in str(tool_result):
        # Error case
        assert tool_result["role"] == "system"
        assert tool_result["content"][0]["type"] == "error"
    else:
        # Success case
        assert tool_result["role"] == "user"
        assert tool_result["content"][0]["type"] == "tool_result"
        assert tool_result["content"][0]["tool_use_id"] == tool_use_block.id
        assert "Here is context retrieved by RAG search" in tool_result["content"][0]["content"]

    # 5. Verify conversation history has correct sequence
    history = test_claude_assistant.conversation_history.get_conversation_history()
    assert len(history) == 2  # Initial message + tool result

    # Initial user message
    assert history[0]["role"] == "user"
    assert history[0]["content"] == user_query

    # Tool result message (from user)
    tool_message = history[1]
    assert tool_message["role"] == "user"
    assert isinstance(tool_message["content"], list)
    assert tool_message["content"][0]["type"] == "tool_result"
    assert tool_message["content"][0]["tool_use_id"] == tool_use_block.id


@pytest.mark.integration
def test_system_prompt_update_and_cache(test_claude_assistant: ClaudeAssistant):
    """
    Test system prompt updates and caching behavior:
    1. Update system prompt with summaries
    2. Verify prompt content
    3. Check cached prompt format for Anthropic API
    """
    test_summaries = [
        {"filename": "test_doc.md", "summary": "Test document about Python", "keywords": ["python", "programming"]}
    ]

    # Update system prompt
    test_claude_assistant.update_system_prompt(test_summaries)

    # Verify prompt content
    assert isinstance(test_claude_assistant.system_prompt, str)
    assert "test_doc.md" in test_claude_assistant.system_prompt
    assert "Test document about Python" in test_claude_assistant.system_prompt

    # Verify cached prompt format for Anthropic API
    cached_prompt = test_claude_assistant.cached_system_prompt()
    assert isinstance(cached_prompt, list)
    assert len(cached_prompt) == 1

    prompt_block = cast(dict[str, Any], cached_prompt[0])
    assert prompt_block["type"] == "text"
    assert isinstance(prompt_block["text"], str)
    assert prompt_block["cache_control"] == {"type": "ephemeral"}
    assert "test_doc.md" in prompt_block["text"]


@pytest.mark.integration
def test_handle_tool_use_error(test_claude_assistant: ClaudeAssistant):
    """Test error handling in tool use."""
    tool_result = test_claude_assistant.handle_tool_use(
        tool_name="rag_search", tool_input={"important_context": "test"}, tool_use_id="test_id"
    )

    assert isinstance(tool_result, dict)
    assert tool_result["role"] == "system"
    assert tool_result["content"][0]["type"] == "error"
