from fastapi import APIRouter, Response, status

from src.api.routes import Routes
from src.infra.logger import get_logger

router = APIRouter()
logger = get_logger()


@router.get(Routes.System.SENTRY_DEBUG)
async def trigger_error() -> Response:
    """Trigger a Sentry error."""
    division_by_zero = 1 / 0
    return Response(status_code=status.HTTP_204_NO_CONTENT)
