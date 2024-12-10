import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.chat.exceptions import TokenLimitError, StreamingError

from src.api.v0.schemas.chat_schemas import MessageType
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.chat.conversation_manager import ConversationManager
from src.models.chat_models import ConversationHistory, Role, StandardEventType
from src.services.chat_service import ChatService
from src.services.data_service import DataService


@pytest.fixture
async def chat_service():
    """Create a ChatService instance with mocked dependencies."""
    claude_assistant = Mock(spec=ClaudeAssistant)
    conversation_manager = Mock(spec=ConversationManager)
    data_service = Mock(spec=DataService)
    data_service.save_conversation = AsyncMock()

    # Setup default conversation
    conversation = ConversationHistory(
        conversation_id=uuid.uuid4(),
        data_sources=[uuid.uuid4()]
    )
    conversation_manager.get_or_create_conversation.return_value = conversation
    conversation_manager.get_conversation_with_pending.return_value = conversation

    return ChatService(
        claude_assistant=claude_assistant,
        conversation_manager=conversation_manager,
        data_service=data_service,
    )


async def test_complete_streaming_flow(chat_service):
    """Test complete streaming flow with persistence."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message"

    # Mock streaming events
    events = [
        Mock(event_type=StandardEventType.MESSAGE_START, content=""),
        Mock(event_type=StandardEventType.TEXT_TOKEN, content="Hello"),
        Mock(event_type=StandardEventType.TEXT_TOKEN, content=" world"),
        Mock(event_type=StandardEventType.MESSAGE_STOP, content=""),
    ]

    # Setup mock response stream
    async def mock_stream():
        for event in events:
            yield event
    chat_service.claude_assistant.stream_response = Mock(return_value=mock_stream())

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify responses
    assert len(responses) == 4
    assert responses[0].message_type == MessageType.TEXT_TOKEN
    assert responses[1].message_type == MessageType.TEXT_TOKEN
    assert responses[1].text == "Hello"
    assert responses[2].text == " world"
    assert responses[3].message_type == MessageType.DONE

    # Verify conversation persistence
    chat_service.conversation_manager.commit_pending.assert_called_once_with(conversation_id)
    chat_service.data_service.save_conversation.assert_called_once_with(conversation_id)


async def test_streaming_error_recovery(chat_service):
    """Test error recovery in streaming flow."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message"

    # Mock streaming error
    async def mock_error():
        raise TokenLimitError("Test error")
        yield  # Make it an async generator
    chat_service.claude_assistant.stream_response = AsyncMock(return_value=mock_error())

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify error response
    assert len(responses) == 1
    assert responses[0].message_type == MessageType.ERROR
    assert "Test error" in responses[0].text

    # Verify cleanup
    chat_service.conversation_manager.rollback_pending.assert_called_once_with(conversation_id)


async def test_streaming_tool_use_flow(chat_service):
    """Test streaming flow with tool use (RAG search)."""
    # Setup test data
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message = "Test message with RAG"

    # Mock streaming events including tool use
    events = [
        Mock(event_type=StandardEventType.MESSAGE_START, content=""),
        Mock(event_type=StandardEventType.TOOL_START, content="rag_search"),
        Mock(event_type=StandardEventType.TEXT_TOKEN, content="Search result"),
        Mock(event_type=StandardEventType.MESSAGE_STOP, content=""),
    ]

    # Setup mock response stream
    async def mock_stream():
        for event in events:
            yield event
    chat_service.claude_assistant.stream_response = Mock(return_value=mock_stream())

    # Collect responses
    responses = []
    async for response in chat_service.get_response(user_id, message, conversation_id):
        responses.append(response)

    # Verify responses
    assert len(responses) == 4
    assert responses[0].message_type == MessageType.TEXT_TOKEN
    assert responses[1].message_type == MessageType.TOOL_USE
    assert responses[1].text == "rag_search"
    assert responses[2].message_type == MessageType.TEXT_TOKEN
    assert responses[2].text == "Search result"
    assert responses[3].message_type == MessageType.DONE

    # Verify conversation persistence
    chat_service.conversation_manager.commit_pending.assert_called_once_with(conversation_id)
    chat_service.data_service.save_conversation.assert_called_once_with(conversation_id)

    # Verify tool use was added to conversation
    chat_service.conversation_manager.add_pending_message.assert_any_call(
        conversation_id=conversation_id,
        role=Role.ASSISTANT,
        text="rag_search"
    )
