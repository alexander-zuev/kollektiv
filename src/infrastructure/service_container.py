from src.core.content.crawler import FireCrawler
from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.supabase_client import SupabaseClient, supabase_client
from src.infrastructure.storage.data_repository import DataRepository
from src.services.content_service import ContentService
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class ServiceContainer:
    """Container object for all services that are initialized in the application."""

    def __init__(self) -> None:
        self.job_manager: JobManager | None = None
        self.firecrawler: FireCrawler | None = None
        self.data_service: DataService | None = None
        self.content_service: ContentService | None = None
        self.repository: DataRepository | None = None
        self.db_client: SupabaseClient | None = None

    def initialize_services(self) -> None:
        """Initialize all services."""
        try:
            self.db_client = supabase_client
            self.repository = DataRepository(db_client=self.db_client)
            self.data_service = DataService(repository=self.repository)
            self.job_manager = JobManager(data_service=self.data_service)
            self.firecrawler = FireCrawler()
            self.content_service = ContentService(self.firecrawler, self.job_manager, self.data_service)
        except Exception:
            logger.error("Error during service initialization happened.")
            raise
