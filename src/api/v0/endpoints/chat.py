from uuid import UUID

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ChatServiceDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.chat_schemas import (
    ConversationListResponse,
    ConversationMessages,
    UserMessage,
)

# Define routers with base prefix only
chat_router = APIRouter(prefix=V0_PREFIX)
conversations_router = APIRouter(prefix=V0_PREFIX)


@chat_router.post(Routes.V0.Chat.CHAT)
async def chat(request: UserMessage, chat_service: ChatServiceDep) -> EventSourceResponse:
    """
    Sends a user message and gets a streaming response.

    Returns Server-Sent Events with tokens.
    """
    async def event_generator():
        conversation_id = request.conversation_id
        try:
            response_stream = chat_service.get_response(
                user_id=request.user_id,
                message=request.message,
                conversation_id=conversation_id
            )
            async for response in response_stream:
                # If conversation_id wasn't provided, get it from the first response
                if conversation_id is None and hasattr(response, 'conversation_id'):
                    conversation_id = response.conversation_id

                if await request.is_disconnected():
                    if conversation_id:
                        await chat_service.conversation_manager.rollback_pending(conversation_id)
                    break
                yield response
        except Exception as e:
            if conversation_id:
                await chat_service.conversation_manager.rollback_pending(conversation_id)
            raise

    return EventSourceResponse(
        event_generator(), media_type="text/event-stream"
    )


# Get all conversations
@conversations_router.get(Routes.V0.Conversations.LIST)
async def list_conversations(chat_service: ChatServiceDep) -> ConversationListResponse:
    """Get grouped list of conversations."""
    return await chat_service.list_conversations()


# Get messages in a conversation
@conversations_router.get(Routes.V0.Conversations.GET)
async def get_conversation(conversation_id: UUID, chat_service: ChatServiceDep) -> ConversationMessages:
    """Get all messages in a conversation."""
    return await chat_service.get_conversation(conversation_id)
