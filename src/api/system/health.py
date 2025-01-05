from fastapi import APIRouter, Response, status

from src.api.dependencies import CeleryAppDep, ChromaManagerDep, RedisManagerDep, SupabaseManagerDep
from src.api.routes import Routes
from src.api.v0.schemas.health_schemas import HealthCheckResponse
from src.infra.logger import get_logger

logger = get_logger()

router = APIRouter()


@router.get(
    Routes.System.HEALTH,
    response_model=HealthCheckResponse,
    responses={
        200: {"description": "All systems operational"},
        503: {"description": "One or more services are down"},
    },
    summary="System Health Status",
    description="Check the health status of all critical system components.",
)
async def health_check(
    response: Response,
    chroma_manager: ChromaManagerDep,
    supabase_manager: SupabaseManagerDep,
    redis_manager: RedisManagerDep,
    celery_app: CeleryAppDep,
) -> HealthCheckResponse:
    """Check if all critical system components are operational.

    This endpoint performs health checks on:
    - Redis connection
    - Supabase connection
    - ChromaDB connection
    - Celery workers

    Returns:
        HealthCheckResponse: System health status
    """
    try:
        # Check Redis - simple ping
        if redis_manager._async_client:
            await redis_manager._async_client.ping()
        else:
            raise RuntimeError("Redis client not initialized")

        # Check Supabase - verify we have a working client
        client = await supabase_manager.get_async_client()
        if not client:
            raise RuntimeError("Supabase client not initialized")

        # Check ChromaDB - heartbeat check
        if chroma_manager._client:
            await chroma_manager._client.heartbeat()
        else:
            raise RuntimeError("ChromaDB client not initialized")

        # Check Celery workers - verify active workers
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        if not active_workers:
            raise RuntimeError("No active Celery workers found")

        return HealthCheckResponse(
            status="operational",
            message="All systems operational",
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthCheckResponse(
            status="down",
            message=f"Service is currently unavailable: {str(e)}",
        )
