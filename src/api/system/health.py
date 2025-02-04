from fastapi import APIRouter, Response, status

from src.api.dependencies import CeleryAppDep, ChromaManagerDep, RedisManagerDep, SupabaseManagerDep
from src.api.routes import CURRENT_API_VERSION, Routes
from src.api.v0.schemas.health_schemas import HealthCheckResponse
from src.infra.decorators import tenacity_retry_wrapper
from src.infra.logger import get_logger
from src.infra.settings import ServiceType, settings

logger = get_logger()

router = APIRouter(prefix=CURRENT_API_VERSION)


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
    """Check if all critical system components are operational. Allows for cold start with the tenacity retry wrapper.

    This endpoint performs health checks on:
    - Redis connection
    - Supabase connection
    - ChromaDB connection
    - Celery workers

    Returns:
        HealthCheckResponse: System health status
    """
    try:
        return await get_services_health(
            chroma_manager=chroma_manager,
            supabase_manager=supabase_manager,
            redis_manager=redis_manager,
            celery_app=celery_app,
        )
    except Exception as e:
        logger.error(f"✗ Health check failed with error: {str(e)}", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthCheckResponse(
            status="down",
            message=f"Service is currently unavailable: {str(e)}",
        )


@tenacity_retry_wrapper(max_attempts=3, min_wait=10, max_wait=30)
async def get_services_health(
    chroma_manager: ChromaManagerDep,
    supabase_manager: SupabaseManagerDep,
    redis_manager: RedisManagerDep,
    celery_app: CeleryAppDep,
) -> HealthCheckResponse:
    """Gets the health of all services, wrapped in the retry decorator."""
    # Check Redis - simple ping
    if redis_manager._async_client:
        await redis_manager._async_client.ping()
    else:
        logger.error("✗ Redis client not initialized")
        raise RuntimeError("Redis client not initialized")

    # Check Supabase - verify we have a working client
    client = await supabase_manager.get_async_client()
    if not client:
        logger.error("✗ Supabase client not initialized")
        raise RuntimeError("Supabase client not initialized")

    # Check ChromaDB - heartbeat check
    if chroma_manager._client:
        await chroma_manager._client.heartbeat()
    else:
        logger.error("✗ ChromaDB client not initialized")
        raise RuntimeError("ChromaDB client not initialized")

    # Check Celery workers - verify active workers
    if settings.service != ServiceType.API:  # Only check workers if we're not the API
        inspector = celery_app.control.inspect()
        logger.debug(f"Celery broker URL: {celery_app.conf.broker_url}")
        try:
            active_workers = inspector.active()
            if not active_workers:
                logger.error("✗ No active Celery workers found")
                raise RuntimeError("No active Celery workers found")
        except ConnectionRefusedError as e:
            logger.error(f"✗ Failed to connect to Celery broker: {str(e)}")
            raise RuntimeError(f"Failed to connect to Celery broker: {str(e)}")
        except Exception as e:
            logger.error(f"✗ Unexpected Celery error: {str(e)}")
            raise

    result: HealthCheckResponse = HealthCheckResponse(
        status="operational",
        message="All systems operational",
    )
    return result
