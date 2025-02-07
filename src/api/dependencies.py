from __future__ import annotations

from typing import Annotated
from uuid import UUID

from celery import Celery
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.v0.schemas.base_schemas import ErrorCode, ErrorResponse
from src.core.content.crawler import FireCrawler
from src.infra.celery.worker import celery_app
from src.infra.external.chroma_manager import ChromaManager
from src.infra.external.redis_manager import RedisManager
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.service_container import ServiceContainer
from src.services.chat_service import ChatService
from src.services.content_service import ContentService
from src.services.job_manager import JobManager

security = HTTPBearer()


def get_container(request: Request) -> ServiceContainer:
    """Retrieve the ServiceContainer instance from app.state."""
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, ServiceContainer):
        raise RuntimeError("ServiceContainer not initialized")
    return container


def get_job_manager(container: Annotated[ServiceContainer, Depends(get_container)]) -> JobManager:
    """Get JobManager from app state."""
    if container.job_manager is None:
        raise RuntimeError("ContentService is not initialized")
    return container.job_manager


def get_crawler(container: Annotated[ServiceContainer, Depends(get_container)]) -> FireCrawler:
    """Get FireCrawler from app state."""
    if container.firecrawler is None:
        raise RuntimeError("ContentService is not initialized")
    return container.firecrawler


def get_content_service(container: Annotated[ServiceContainer, Depends(get_container)]) -> ContentService:
    """Get ContentService from app state."""
    if container.content_service is None:
        raise RuntimeError("ContentService is not initialized")
    return container.content_service


def get_chat_service(container: Annotated[ServiceContainer, Depends(get_container)]) -> ChatService:
    """Get ChatService from app state."""
    if container.chat_service is None:
        raise RuntimeError("ChatService is not initialized")
    return container.chat_service


def get_chroma_manager(container: Annotated[ServiceContainer, Depends(get_container)]) -> ChromaManager:
    """Get ChromaManager from app state."""
    if container.chroma_manager is None:
        raise RuntimeError("ChromaManager is not initialized")
    return container.chroma_manager


def get_redis_manager(container: Annotated[ServiceContainer, Depends(get_container)]) -> RedisManager:
    """Get RedisManager from app state."""
    if container.async_redis_manager is None:
        raise RuntimeError("RedisManager is not initialized")
    return container.async_redis_manager


def get_supabase_manager(container: Annotated[ServiceContainer, Depends(get_container)]) -> SupabaseManager:
    """Get SupabaseManager from app state."""
    if container.supabase_manager is None:
        raise RuntimeError("SupabaseManager is not initialized")
    return container.supabase_manager


def get_celery_app(container: Annotated[ServiceContainer, Depends(get_container)]) -> Celery:
    """Get Celery app from app state."""
    if celery_app is None:
        raise RuntimeError("Celery app is not initialized")
    return celery_app


async def get_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    supabase_manager: Annotated[SupabaseManager, Depends(get_supabase_manager)],
) -> UUID:
    """Retrieve the user id from the supabase client."""
    if credentials is None:
        raise HTTPException(status_code=401, detail=ErrorResponse(code=ErrorCode.CLIENT_ERROR, detail="Unauthorized"))

    supabase_client = await supabase_manager.get_async_client()
    user_response = await supabase_client.auth.get_user(credentials.credentials)
    return UUID(user_response.user.id)


# Type aliases for cleaner dependency injection
ContainerDep = Annotated[ServiceContainer, Depends(get_container)]
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
FireCrawlerDep = Annotated[FireCrawler, Depends(get_crawler)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ChromaManagerDep = Annotated[ChromaManager, Depends(get_chroma_manager)]
SupabaseManagerDep = Annotated[SupabaseManager, Depends(get_supabase_manager)]
RedisManagerDep = Annotated[RedisManager, Depends(get_redis_manager)]
CeleryAppDep = Annotated[Celery, Depends(get_celery_app)]
UserIdDep = Annotated[UUID, Depends(get_user_id)]
