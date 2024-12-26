from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import ContentServiceDep
from src.api.routes import V0_PREFIX, Routes
from src.api.v0.schemas.base_schemas import ErrorResponse, SourceResponse
from src.api.v0.schemas.sources_schemas import AddContentSourceRequest
from src.infra.logger import get_logger

logger = get_logger()
router = APIRouter(prefix=f"{V0_PREFIX}{Routes.V0.CONTENT}")


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
