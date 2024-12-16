from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.exceptions import RequestValidationError
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ChatServiceDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.base_schemas import ErrorResponse
from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    LLMResponse,
    UserMessage,
)
from src.core._exceptions import DatabaseError, EntityNotFoundError, NonRetryableLLMError, RetryableLLMError
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

        async def event_stream() -> AsyncIterator[str]:
            async for event in chat_service.get_response(user_id=request.user_id, message=request.message):
                yield event.model_dump_json()

        return EventSourceResponse(event_stream(), media_type="text/event-stream")
    except NonRetryableLLMError as e:
        raise HTTPException(
            status_code=500, detail=f"A non-retryable error occurred in the system:: {str(e)}. We are on it."
        ) from e
    except RetryableLLMError as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred in the system:: {str(e)}. Can you please try again?"
        ) from e


# Get all conversations
@conversations_router.get(
    Routes.V0.Conversations.LIST,
    response_model=ConversationListResponse,
    responses={
        200: {"model": ConversationListResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_conversations(user_id: UUID, chat_service: ChatServiceDep) -> ConversationListResponse:
    """Get grouped list of conversations."""
    try:
        return await chat_service.get_conversations(user_id)
    except DatabaseError as e:
        logger.error(f"Database error while getting conversations for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Database Error", code=500, detail="Failed to retrieve conversations."
            ).model_dump(),
        ) from e
    except RequestValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="Bad Request", code=400, detail="Invalid request data.").model_dump(),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error while getting conversations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Internal Server Error", code=500, detail="An unexpected error occurred."
            ).model_dump(),
        ) from e


# Get messages in a conversation
@conversations_router.get(
    Routes.V0.Conversations.GET,
    response_model=Conversation,
    responses={
        200: {"model": Conversation},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_conversation(conversation_id: UUID, chat_service: ChatServiceDep) -> Conversation:
    """Get all messages in a conversation."""
    try:
        return await chat_service.get_conversation(conversation_id)
    # Handle case where conversation is not found
    except EntityNotFoundError as e:
        logger.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="Not Found", code=404, detail="Conversation not found.").model_dump(),
        ) from e
    # Handle all other database errors
    except DatabaseError as e:
        logger.error(f"Database error while getting conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Database Error", code=500, detail="Failed to retrieve conversation."
            ).model_dump(),
        ) from e
    # Handle case when the client sends invalid request
    except RequestValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="Bad Request", code=400, detail="Invalid request data.").model_dump(),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error while getting conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Internal Server Error", code=500, detail="An unexpected error occurred."
            ).model_dump(),
        ) from e
