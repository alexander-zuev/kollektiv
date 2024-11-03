from fastapi import APIRouter, HTTPException, status

from src.api.deps import ContentServiceDep
from src.api.routes import Routes
from src.api.v0.content.schemas import AddContentSourceRequest, ContentSourceResponse, ContentSourceStatus
from src.infrastructure.config.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.get(Routes.V0.Content.SOURCES, response_model=list[ContentSourceResponse])
async def list_sources(content_service: ContentServiceDep) -> list[ContentSourceResponse]:
    """List all content sources."""
    return await content_service.list_sources()


@router.post(Routes.V0.Content.SOURCES, response_model=ContentSourceResponse, status_code=status.HTTP_201_CREATED)
async def add_source(request: AddContentSourceRequest, content_service: ContentServiceDep) -> ContentSourceResponse:
    """
    Add a new content source.

    Args:
        request: Content source details
        content_service: Injected content service

    Returns:
        ContentSourceResponse: Created content source details

    Raises:
        HTTPException: If source creation fails
    """
    try:
        return await content_service.add_source(request)
    except Exception as e:
        logger.error(f"Failed to add source: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get(Routes.V0.Content.SOURCE, response_model=ContentSourceResponse)
async def get_source(source_id: str, content_service: ContentServiceDep) -> ContentSourceResponse:
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
