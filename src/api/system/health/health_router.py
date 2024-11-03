from fastapi import APIRouter, Response, status

from src.api.routes import Routes
from src.infrastructure.config.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.get(
    Routes.System.HEALTH,
    responses={
        200: {"description": "All systems operational"},
        503: {"description": "Service is currently unavailable"},
    },
    summary="System Health Status",
    description="Provides the current operational status of the API service.",
)
async def health_check(response: Response):
    """Check if the API service is operational.

    This endpoint is used by monitoring systems to verify service health
    and by users to check system status.

    Returns:
        dict: Current system status and version information
    """
    try:
        return {
            "status": "operational",
            "message": "All systems operational",
            # TODO: Add version from the package
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "message": "Service is currently unavailable"}
