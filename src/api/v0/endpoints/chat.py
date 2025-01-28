from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ChatServiceDep, SupabaseManagerDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.base_schemas import ErrorResponse
from src.core._exceptions import DatabaseError, EntityNotFoundError, NonRetryableLLMError, RetryableLLMError
from src.infra.logger import get_logger
from src.models.chat_models import (
    ConversationHistoryResponse,
    ConversationListResponse,
    FrontendChatEvent,
    UserMessage,
)

# Define routers with base prefix only
chat_router = APIRouter(prefix=V0_PREFIX)
conversations_router = APIRouter(prefix=V0_PREFIX)

logger = get_logger()

security = HTTPBearer()


@chat_router.post(
    Routes.V0.Chat.CHAT,
    response_model=FrontendChatEvent,
    responses={
        200: {"model": FrontendChatEvent},
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
        logger.debug(f"POST /chat request for debugging: {request.model_dump(serialize_as_any=True)}")

        async def event_stream() -> AsyncIterator[str]:
            async for event in chat_service.get_response(user_message=request):
                yield event.model_dump_json(serialize_as_any=True)

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


# TODO: Refactor user id into a UserContext service that would be accesssible by any service / endpoint
# TODO: API layer would set the user id in the request context
# TODO: Chat service would get the user id from the user context service


# Get messages in a conversation
@conversations_router.get(
    Routes.V0.Conversations.GET,
    response_model=ConversationHistoryResponse,
    responses={
        200: {"model": ConversationHistoryResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_conversation(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    conversation_id: UUID,
    chat_service: ChatServiceDep,
    supabase: SupabaseManagerDep,
) -> ConversationHistoryResponse:
    """Get all messages in a conversation."""
    try:
        # Get the client
        supabase_client = await supabase.get_async_client()

        # Get the user
        user_response = await supabase_client.auth.get_user(credentials.credentials)
        user_id = UUID(user_response.user.id)
        logger.debug(f"User ID: {user_id}")

        # Get the conversation
        return await chat_service.get_conversation(conversation_id, user_id)
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
