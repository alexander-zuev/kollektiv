from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import ContentServiceDep, UserIdDep
from src.api.routes import CURRENT_API_VERSION, Routes
from src.api.v0.schemas.base_schemas import ErrorCode, ErrorResponse
from src.core._exceptions import CrawlerError, NonRetryableError
from src.infra.logger import get_logger
from src.models.content_models import (
    AddContentSourceRequest,
    AddContentSourceResponse,
    SourceEvent,
    SourceOverview,
    SourceSummary,
)

logger = get_logger()
router = APIRouter(prefix=f"{CURRENT_API_VERSION}")


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
    logger.debug(f"Dumping request for debugging: {request.model_dump()}")
    try:
        response = await content_service.add_source(request)
        return response
    except (CrawlerError, NonRetryableError) as e:
        raise HTTPException(status_code=500, detail=ErrorResponse(code=ErrorCode.SERVER_ERROR, detail=str(e))) from e


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
                event_json = event.model_dump_json()
                logger.debug(f"Printing event for debugging: {event_json}")
                yield event_json

        return EventSourceResponse(event_stream(), media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=ErrorResponse(code=ErrorCode.CLIENT_ERROR, detail=str(e))) from e


@router.get(
    Routes.V0.Sources.SOURCES,
    response_model=list[SourceOverview],
    responses={
        200: {"model": list[SourceOverview]},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    status_code=status.HTTP_200_OK,
)
async def get_sources(content_service: ContentServiceDep, user_id: UserIdDep) -> list[SourceSummary]:
    """Returns a list of all sources that a user has."""
    try:
        return await content_service.get_sources(user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                code=ErrorCode.SERVER_ERROR,
                detail="An error occured while trying to get the list of sources. We are working on it already.",
            ),
        ) from e


# @router.patch(
#     Routes.V0.Sources.SOURCES,
#     response_model=UpdateSourcesResponse,
#     responses={
#         200: {"model": UpdateSourcesResponse},
#         400: {"model": ErrorResponse},
#         404: {"model": ErrorResponse},
#         500: {"model": ErrorResponse},
#     },
#     status_code=status.HTTP_200_OK,
# )
# async def update_sources(request: UpdateSourcesRequest, content_service: ContentServiceDep) -> UpdateSourcesResponse:
#     """Updates a source."""
#     try:
#         return await content_service.update_sources(request)
#     # How do we handle 400 and 404? What are those?
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail="An error occured while trying to update the source. We are working on it already.",
#         ) from e


# @router.delete(
#     Routes.V0.Sources.SOURCES,
#     response_model=DeleteSourcesResponse,
#     responses={
#         200: {"model": DeleteSourcesResponse},  # successfully deleted
#         404: {"model": ErrorResponse},  # Source not found
#         500: {"model": ErrorResponse},  # Internal error
#     },
#     status_code=status.HTTP_200_OK,
# )
# async def delete_sources(request: DeleteSourcesRequest, content_service: ContentServiceDep) -> DeleteSourcesResponse:
#     """Deletes a source."""
#     try:
#         return await content_service.delete_sources(request)
#     # How do we handle 404?
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail="An error occured while trying to delete the source. We are working on it already.",
#         ) from e
