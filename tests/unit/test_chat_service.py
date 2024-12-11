import pytest
from unittest.mock import AsyncMock, Mock, call
from uuid import UUID

from src.services.chat_service import ChatService
from src.models.chat_models import (
    StandardEvent,
    StandardEventType,
    ConversationHistory,
    Role,
    MessageContent,
)
from src.api.v0.schemas.chat_schemas import LLMResponse, MessageType
from src.core.chat.claude_assistant import ClaudeAssistant
from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.conversation_manager import ConversationManager
from src.services.data_service import DataService


@pytest.fixture
def mock_claude_assistant():
    """Mock Claude assistant."""
    mock = AsyncMock(spec=ClaudeAssistant)

    async def mock_stream(*args, **kwargs):
        events = [
            StandardEvent(event_type=StandardEventType.MESSAGE_START, content=MessageContent.from_str("")),
            StandardEvent(event_type=StandardEventType.TEXT_TOKEN, content=MessageContent.from_str("Hello")),
            StandardEvent(event_type=StandardEventType.MESSAGE_STOP, content=MessageContent.from_str("")),
            StandardEvent(event_type=StandardEventType.FULL_MESSAGE, content=MessageContent.from_str("Hello")),
        ]
        for event in events:
            yield event

    mock.stream_response.side_effect = mock_stream
    return mock


@pytest.fixture
def mock_conversation_manager():
    """Create a mock conversation manager."""
    manager = AsyncMock(spec=ConversationManager)
    conversation_id = UUID("12345678-1234-5678-1234-567812345678")

    # Create conversation history for responses
    conversation_history = ConversationHistory(
        conversation_id=conversation_id,
        messages=[],
    )

    # Set up mock returns
    manager.get_or_create_conversation.return_value = conversation_history
    manager.get_conversation_with_pending.return_value = conversation_history
    return manager


@pytest.fixture
def mock_data_service():
    """Mock data service."""
    mock = AsyncMock(spec=DataService)
    return mock


@pytest.fixture
def chat_service(
    mock_claude_assistant: AsyncMock,
    mock_conversation_manager: AsyncMock,
    mock_data_service: AsyncMock,
) -> ChatService:
    """Create chat service with mocked dependencies."""
    return ChatService(claude_assistant=mock_claude_assistant, conversation_manager=mock_conversation_manager, data_service=mock_data_service)


@pytest.mark.asyncio
async def test_get_response_streaming_basic_flow(chat_service, mock_conversation_manager):
    """Test basic streaming response flow from chat service."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"

    events = []
    async for event in chat_service.get_response(user_id, message):
        events.append(event)

    # Verify events content
    assert len(events) == 3  # conversation_id + text_token + done

    # Verify conversation_id event
    assert events[0].message_type == MessageType.CONVERSATION_ID
    assert UUID(events[0].text) == mock_conversation_manager.get_conversation_with_pending.return_value.conversation_id

    # Verify text token event
    assert events[1].message_type == MessageType.TEXT_TOKEN
    assert "Hello" in events[1].text

    # Verify done event
    assert events[2].message_type == MessageType.DONE
    assert "Hello" in events[2].text

    # Verify conversation manager calls
    mock_conversation_manager.get_or_create_conversation.assert_called_once()
    mock_conversation_manager.add_pending_message.assert_called_once()
    mock_conversation_manager.commit_pending.assert_called_once()


@pytest.mark.asyncio
async def test_get_response_with_tool_use(chat_service, mock_conversation_manager):
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"

    async def mock_stream(*args, **kwargs):
        events = [
            StandardEvent(event_type=StandardEventType.TOOL_START, content=MessageContent.from_str("Using tool X")),
            StandardEvent(event_type=StandardEventType.TOOL_RESULT, content=MessageContent.from_str("Tool result")),
            StandardEvent(event_type=StandardEventType.TEXT_TOKEN, content=MessageContent.from_str("Response")),
            StandardEvent(event_type=StandardEventType.FULL_MESSAGE, content=MessageContent.from_str("Response")),
        ]
        for event in events:
            yield event

    chat_service.claude_assistant.stream_response.side_effect = mock_stream

    events = []
    async for event in chat_service.get_response(user_id, message):
        events.append(event)

    assert len(events) == 4  # conversation_id + tool_use + text_token + done

    # Verify conversation_id event
    assert events[0].message_type == MessageType.CONVERSATION_ID
    assert UUID(events[0].text) == mock_conversation_manager.get_conversation_with_pending.return_value.conversation_id

    # Verify tool use event
    assert events[1].message_type == MessageType.TOOL_USE
    assert "Using tool X" in str(events[1].text)  # Convert blocks representation to string for comparison

    # Verify text token event
    assert events[2].message_type == MessageType.TEXT_TOKEN
    assert "Response" in str(events[2].text)  # Convert blocks representation to string for comparison

    # Verify done event
    assert events[3].message_type == MessageType.DONE
    assert "Response" in str(events[3].text)  # Convert blocks representation to string for comparison

    # Verify conversation manager calls
    mock_conversation_manager.get_or_create_conversation.assert_called_once()
    mock_conversation_manager.add_pending_message.assert_called_once()
    mock_conversation_manager.add_message.assert_called_once()
    mock_conversation_manager.commit_pending.assert_called_once()


@pytest.mark.asyncio
async def test_get_response_retryable_error(chat_service: ChatService):
    """Test handling of retryable errors."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"

    async def mock_stream(*args, **kwargs):
        if True:  # This ensures the generator is properly initialized
            raise RetryableLLMError("API timeout", original_error=Exception("API timeout"))
        yield StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content=MessageContent.from_str(""),
        )

    chat_service.claude_assistant.stream_response = mock_stream

    events = []
    async for event in chat_service.get_response(user_id, message):
        events.append(event)

    assert len(events) == 2  # conversation_id + error
    assert events[0].message_type == MessageType.CONVERSATION_ID
    assert events[1].message_type == MessageType.ERROR
    assert "API timeout" in events[1].text


@pytest.mark.asyncio
async def test_get_response_non_retryable_error(chat_service: ChatService):
    """Test handling of non-retryable errors."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"

    async def mock_stream(*args, **kwargs):
        if True:  # This ensures the generator is properly initialized
            raise NonRetryableLLMError("Invalid request", original_error=Exception("Invalid request"))
        yield StandardEvent(
            event_type=StandardEventType.MESSAGE_START,
            content=MessageContent.from_str(""),
        )

    chat_service.claude_assistant.stream_response = mock_stream

    events = []
    async for event in chat_service.get_response(user_id, message):
        events.append(event)

    assert len(events) == 2  # conversation_id + error
    assert events[0].message_type == MessageType.CONVERSATION_ID
    assert events[1].message_type == MessageType.ERROR
    assert "Invalid request" in events[1].text


@pytest.mark.asyncio
async def test_prepare_conversation_new(chat_service: ChatService):
    """Test preparing a new conversation."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"
    result = await chat_service._prepare_conversation(conversation_id=None, message=message, user_id=user_id)
    assert isinstance(result, ConversationHistory)
    chat_service.conversation_manager.get_or_create_conversation.assert_called_once_with(
        user_id=user_id,
        title="Test Conversation",
        data_sources=[],
    )


@pytest.mark.asyncio
async def test_prepare_conversation_existing(chat_service: ChatService):
    """Test preparing an existing conversation."""
    conversation_id = UUID("12345678-1234-5678-1234-567812345678")
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = "Test message"

    result = await chat_service._prepare_conversation(conversation_id, message, user_id)

    # Verify get_conversation_with_pending is called twice:
    # 1. To get the initial conversation
    # 2. To get the conversation with the new pending message
    chat_service.conversation_manager.get_conversation_with_pending.assert_has_calls([
        call(conversation_id),
        call(conversation_id),
    ])

    # Verify add_pending_message is called with correct parameters
    chat_service.conversation_manager.add_pending_message.assert_called_once_with(
        conversation_id=conversation_id,
        role=Role.USER,
        content=message,
    )

    assert result == chat_service.conversation_manager.get_conversation_with_pending.return_value


@pytest.mark.asyncio
async def test_get_response_handles_empty_message(chat_service):
    """Test that get_response handles empty messages appropriately."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = ""

    with pytest.raises(ValueError, match="Message cannot be empty"):
        await chat_service.get_response(user_id, message).__anext__()


@pytest.mark.asyncio
async def test_get_response_handles_none_message(chat_service):
    """Test that get_response handles None messages appropriately."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    message = None

    with pytest.raises(ValueError, match="Message cannot be None"):
        await chat_service.get_response(user_id, message).__anext__()


@pytest.mark.asyncio
async def test_list_conversations(chat_service, mock_data_service):
    """Test listing conversations."""
    user_id = UUID("98765432-9876-5432-9876-987654321098")
    with pytest.raises(NotImplementedError):
        await chat_service.list_conversations()


@pytest.mark.asyncio
async def test_get_conversation(chat_service, mock_data_service):
    """Test getting a conversation."""
    conversation_id = UUID("12345678-1234-5678-1234-567812345678")
    with pytest.raises(NotImplementedError):
        await chat_service.get_conversation(conversation_id)
