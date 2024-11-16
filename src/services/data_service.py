from typing import Any
from uuid import UUID

from src.api.v0.schemas.sources_schemas import AddContentSourceRequest
from src.infrastructure.common.decorators import generic_error_handler
from src.infrastructure.config.logger import get_logger
from src.infrastructure.storage.supabase.supabase_operations import DataRepository
from src.models.common.jobs import Job
from src.models.content.content_source_models import DataSource
from src.models.content.firecrawl_models import CrawlResult

logger = get_logger()


class DataService:
    """Service layer responsible for coordinating data operations and business logic.

    This service acts as an intermediary between the application and data access layer.
    It handles:
    - Business logic and validation
    - Data transformation and mapping
    - Coordination between multiple repositories if needed
    - Transaction management
    - Event emission for data changes

    The service uses DataRepository for actual database operations while focusing on
    higher-level business operations and data integrity.
    """

    def __init__(self, datasource_repo: DataRepository):
        self.datasource_repo = datasource_repo
        logger.debug("Initialized data service")

    @generic_error_handler
    async def save_datasource(self, data_source: DataSource) -> None:
        """Persists data source entry. Uses datasource repo."""
        await self.datasource_repo.save_datasource(data_source=data_source)

    @generic_error_handler
    async def update_datasource(self, source_id: UUID, updates: dict[str, Any]) -> DataSource:
        """Updates a given datasource with provided field updates."""
        # Get current source first
        current_source = await self.datasource_repo.retrieve_datasource(source_id)

        # Apply updates to current source
        updated_source = current_source.model_copy(update=updates)

        # Save updated source
        await self.datasource_repo.update_datasource(updated_source)

        return DataSource.model_validate(updated_source)

    @generic_error_handler
    async def retrieve_datasource(self, source_id: UUID) -> DataSource:
        """Retrieves a data source object."""
        result = await self.datasource_repo.retrieve_datasource(source_id)
        data_source = DataSource.model_validate(result)
        logger.debug(f"Retrieved source id {data_source.source_id} from the db.")
        return data_source

    async def list_datasources(self) -> list[DataSource]:
        """Lists all datasources."""
        results = await self.datasource_repo.list_datasources()
        return [DataSource.model_validate(result) for result in results]

    async def save_user_request(self, request: AddContentSourceRequest) -> None:
        """Saves user request to add content."""
        await self.datasource_repo.save_user_request(request=request)

    @generic_error_handler
    async def save_job(self, job: Job) -> None:
        """Persists job object in the database."""
        logger.debug(f"Saving job {job.job_id}")
        await self.datasource_repo.save_job(job=job)

    @generic_error_handler
    async def retrieve_job(self, job_id: UUID) -> Job:
        """Retrieves job from the database."""
        logger.debug(f"Retrieving job {job_id}")
        result = await self.datasource_repo.retrieve_job(job_id=job_id)
        return Job.model_validate(result)

    @generic_error_handler
    async def get_job_by_firecrawl_id(self, firecrawl_id: str) -> Job:
        """Retrieves job by FireCrawl ID."""
        logger.debug(f"Retrieving job with FireCrawl ID {firecrawl_id}")
        result = await self.datasource_repo.get_job_by_firecrawl_id(firecrawl_id=firecrawl_id)
        return Job.model_validate(result)

    @generic_error_handler
    async def list_jobs(self, source_id: UUID | None = None) -> list[Job]:
        """Lists all jobs, optionally filtered by source_id."""
        logger.debug(f"Listing jobs{' for source ' + str(source_id) if source_id else ''}")
        results = await self.datasource_repo.list_jobs(source_id=source_id)
        return [Job.model_validate(result) for result in results]

    async def save_crawl_result(self, crawl_result: CrawlResult) -> None:
        """Persists crawl results in the database."""
        pass

    async def retrieve_crawl_results(self, crawl_result_ids: list[UUID]) -> list[CrawlResult]:
        """Retrieves crawl results from the database."""
        results = await self.datasource_repo.retrieve_crawl_results(crawl_result_ids)
        return [CrawlResult.model_validate(result) for result in results]
