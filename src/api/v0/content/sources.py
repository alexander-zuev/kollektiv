from fastapi import APIRouter, HTTPException, status

from src.api.routes import Routes
from src.api.v0.content.schemas import AddContentSourceRequest, ContentSourceResponse, ContentSourceStatus
from src.core.content.crawler.crawler import FireCrawler
from src.infrastructure.config.logger import get_logger
from src.services.content_service import ContentService

logger = get_logger()
router = APIRouter()
content_service = ContentService(crawler=FireCrawler())


# POST: add new source
# GET: list all sources
# GET: get source by id
# DELETE: delete source by id
# GET: get status of source by id


@router.get(Routes.V0.Content.SOURCES, response_model=list[ContentSourceResponse])
async def list_sources() -> list[ContentSourceResponse]:
    """List all content sources."""
    pass


@router.post(Routes.V0.Content.SOURCES, response_model=ContentSourceResponse, status_code=status.HTTP_201_CREATED)
async def add_source(request: AddContentSourceRequest) -> ContentSourceResponse:
    """Add a new content source."""
    try:
        return await content_service.add_source(request)
    except Exception as e:
        logger.error(f"Failed to add source: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(Routes.V0.Content.SOURCE, response_model=ContentSourceResponse)
async def get_source(source_id: str) -> ContentSourceResponse:
    """Get a content source by ID."""
    pass


@router.delete(Routes.V0.Content.SOURCE, status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str) -> None:
    """Delete a content source by ID."""
    pass


@router.get(Routes.V0.Content.SOURCE_STATUS, response_model=ContentSourceStatus)
async def get_source_status(source_id: str) -> ContentSourceStatus:
    """Get the status of a content source by ID."""
    pass
