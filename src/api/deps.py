from typing import Annotated

from fastapi import Depends, FastAPI

from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.services.content_service import ContentService
from app import app


def get_content_service(app: FastAPI = Depends()) -> ContentService:
    """Get ContentService from app state."""
    return app.state.content_service


def get_job_manager(app: FastAPI = Depends()) -> JobManager:
    """Get JobManager from app state."""
    return app.state.job_manager


def get_crawler(app: FastAPI = Depends()) -> FireCrawler:
    """Get FireCrawler from app state."""
    return app.state.firecrawler


# Type aliases for cleaner dependency injection
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
FireCrawlerDep = Annotated[FireCrawler, Depends(get_crawler)]
