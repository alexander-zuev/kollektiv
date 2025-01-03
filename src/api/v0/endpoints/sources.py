from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ContentServiceDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.base_schemas import ErrorResponse
from src.infra.logger import get_logger
from src.models.content_models import AddContentSourceRequest, AddContentSourceResponse, SourceEvent

logger = get_logger()
router = APIRouter(prefix=f"{V0_PREFIX}")


@router.post(
    Routes.V0.Sources.SOURCES,
    response_model=AddContentSourceResponse,
    responses={
        201: {"model": AddContentSourceResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    status_code=status.HTTP_201_CREATED,
)
async def add_source(
    request: AddContentSourceRequest,
    content_service: ContentServiceDep,
) -> AddContentSourceResponse:
    """
    Add a new content source.

    Args:
        request: Content source details
        content_service: Injected content service

    Returns:
        AddContentSourceResponse: Created content source details

    Raises:
        HTTPException: If source creation fails
    """
    try:
        source_response = await content_service.add_source(request)
        return source_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to add source: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    Routes.V0.Sources.SOURCE_EVENTS,
    response_model=SourceEvent,
    responses={
        200: {"model": SourceEvent},
        404: {"model": ErrorResponse, "description": "Source not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=status.HTTP_200_OK,
)
async def stream_source_events(source_id: UUID, content_service: ContentServiceDep) -> EventSourceResponse:
    """Returns a stream of events for a source."""
    try:

        async def event_stream() -> AsyncGenerator[str, None]:
            async for event in content_service.stream_source_events(source_id=source_id):
                event = event.model_dump_json()
                logger.debug(f"Printing event for debugging: {event}")
                yield event

        return EventSourceResponse(event_stream(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
