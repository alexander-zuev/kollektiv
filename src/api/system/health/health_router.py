from fastapi import APIRouter

from src.api.routes import Routes

router = APIRouter()


@router.get(Routes.System.HEALTH)
async def health_check():
    """Check the health of the API."""
    return {"status": "healthy"}
