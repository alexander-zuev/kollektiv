from typing import Annotated

from fastapi import Depends, FastAPI

from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.services.content_service import ContentService


def get_app() -> FastAPI:
    """Get FastAPI application instance."""
    from .app import app  # Import inside the function

    return app


def get_content_service(app: FastAPI = Depends(get_app)) -> ContentService:
    """Get ContentService from app state."""
    return app.state.content_service


def get_job_manager(app: FastAPI = Depends(get_app)) -> JobManager:
    """Get JobManager from app state."""
    return app.state.job_manager


def get_crawler(app: FastAPI = Depends(get_app)) -> FireCrawler:
    """Get FireCrawler from app state."""
    return app.state.firecrawler


# Type aliases for cleaner dependency injection
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
FireCrawlerDep = Annotated[FireCrawler, Depends(get_crawler)]
