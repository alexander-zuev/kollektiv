from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.core.content.crawler import FireCrawler
from src.infrastructure.service_container import ServiceContainer
from src.services.content_service import ContentService
from src.services.job_manager import JobManager


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


# Type aliases for cleaner dependency injection
ContainerDep = Annotated[ServiceContainer, Depends(get_container)]
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
FireCrawlerDep = Annotated[FireCrawler, Depends(get_crawler)]
