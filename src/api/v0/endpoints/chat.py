from uuid import UUID

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ChatServiceDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.base_schemas import ErrorResponse
from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    LLMResponse,
    UserMessage,
)
from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.models.chat_models import Conversation

# Define routers with base prefix only
chat_router = APIRouter(prefix=V0_PREFIX)
conversations_router = APIRouter(prefix=V0_PREFIX)


@chat_router.post(
    Routes.V0.Chat.CHAT,
    response_model=LLMResponse,
    responses={
        200: {"model": LLMResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat(request: UserMessage, chat_service: ChatServiceDep) -> EventSourceResponse:
    """
    Sends a user message and gets a streaming response.

    Returns Server-Sent Events with tokens.
    """
    try:
        return EventSourceResponse(
            chat_service.get_response(user_id=request.user_id, message=request.message), media_type="text/event-stream"
        )
    except NonRetryableLLMError as e:
        raise HTTPException(
            status_code=500, detail=f"A non-retryable error occurred in the system:: {str(e)}. We are on it."
        ) from e
    except RetryableLLMError as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred in the system:: {str(e)}. Can you please try again?"
        ) from e


# Get all conversations
@conversations_router.get(Routes.V0.Conversations.LIST, response_model=ConversationListResponse)
async def list_conversations(user_id: UUID, chat_service: ChatServiceDep) -> ConversationListResponse:
    """Get grouped list of conversations."""
    return await chat_service.get_conversations(user_id)


# Get messages in a conversation
@conversations_router.get(Routes.V0.Conversations.GET, response_model=Conversation)
async def get_conversation(user_id: UUID, conversation_id: UUID, chat_service: ChatServiceDep) -> Conversation:
    """Get all messages in a conversation."""
    return await chat_service.get_conversation(user_id, conversation_id)
