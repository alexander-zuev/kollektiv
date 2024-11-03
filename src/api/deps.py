from typing import Annotated

from fastapi import Depends

from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.infrastructure.common.file_manager import FileManager
from src.infrastructure.config.settings import JOB_FILE_DIR, RAW_DATA_DIR
from src.services.content_service import ContentService


async def get_job_manager() -> JobManager:
    """Get JobManager instance with proper configuration."""
    return JobManager(storage_dir=JOB_FILE_DIR)


async def get_file_manager() -> FileManager:
    """Get FileManager instance with proper configuration."""
    return FileManager(raw_data_dir=RAW_DATA_DIR)


async def get_crawler(
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
    file_manager: Annotated[FileManager, Depends(get_file_manager)],
) -> FireCrawler:
    """Get configured FireCrawler instance."""
    return FireCrawler(job_manager=job_manager, file_manager=file_manager)


async def get_content_service(crawler: Annotated[FireCrawler, Depends(get_crawler)]) -> ContentService:
    """Get ContentService with all required dependencies."""
    return ContentService(crawler=crawler)


# Create type aliases for cleaner dependency injection
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
