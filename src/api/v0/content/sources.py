from fastapi import APIRouter, HTTPException, status

from src.api.deps import ContentServiceDep
from src.api.routes import Routes
from src.api.v0.base_schemas import ErrorResponse, SourceResponse
from src.api.v0.content.schemas import AddContentSourceRequest, SourceAPIResponse
from src.infrastructure.config.logger import get_logger
from src.models.content.content_source_models import SourceStatus as ContentSourceStatus

logger = get_logger()
router = APIRouter()


@router.get(Routes.V0.Content.SOURCES, response_model=list[SourceAPIResponse])
async def list_sources(content_service: ContentServiceDep) -> list[SourceAPIResponse]:
    """List all content sources."""
    return await content_service.list_sources()


@router.post(
    Routes.V0.Content.SOURCES,
    response_model=SourceResponse,
    responses={
        201: {"model": SourceResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    status_code=status.HTTP_201_CREATED,
)
async def add_source(
    request: AddContentSourceRequest,
    content_service: ContentServiceDep,
) -> SourceResponse:
    """
    Add a new content source.

    Args:
        request: Content source details
        content_service: Injected content service

    Returns:
        SourceResponse: Created content source details

    Raises:
        HTTPException: If source creation fails
    """
    try:
        source = await content_service.add_source(request)
        return SourceResponse(success=True, data=source, message="Source added successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to add source: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(Routes.V0.Content.SOURCE, response_model=SourceAPIResponse)
async def get_source(source_id: str, content_service: ContentServiceDep) -> SourceAPIResponse:
    """Get a content source by ID."""
    return await content_service.get_source(source_id)


@router.delete(Routes.V0.Content.SOURCE, status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, content_service: ContentServiceDep) -> None:
    """Delete a content source by ID."""
    pass


@router.get(Routes.V0.Content.SOURCE_STATUS, response_model=ContentSourceStatus)
async def get_source_status(source_id: str, content_service: ContentServiceDep) -> ContentSourceStatus:
    """Get the status of a content source by ID."""
    return await content_service.get_source_status(source_id)
