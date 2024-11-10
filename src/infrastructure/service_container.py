from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.infrastructure.config.settings import JOB_FILE_DIR
from src.services.content_service import ContentService


class ServiceContainer:
    """Container object for all services that are initialized in the application."""

    def __init__(self) -> None:
        self.job_manager: JobManager | None = None
        self.firecrawler: FireCrawler | None = None
        self.content_service: ContentService | None = None

    def initialize_services(self) -> None:
        """Initialize all services."""
        self.job_manager = JobManager(storage_dir=JOB_FILE_DIR)
        self.firecrawler = FireCrawler()
        self.content_service = ContentService(self.firecrawler, self.job_manager)
