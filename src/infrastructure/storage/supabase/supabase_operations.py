from uuid import UUID

from src.api.v0.schemas.sources_schemas import AddContentSourceRequest
from src.core._exceptions import JobNotFoundError, NotImplementedError
from src.infrastructure.common.decorators import supabase_operation
from src.infrastructure.config.logger import get_logger
from src.infrastructure.external.supabase_client import SupabaseClient
from src.models.common.jobs import Job
from src.models.content.content_source_models import DataSource
from src.models.content.firecrawl_models import CrawlResult

logger = get_logger()


class DataRepository:
    """Repository that handles all database operations for content-related data.

    This repository is responsible for direct database interactions using Supabase.
    It provides a clean data access layer that:
    - Executes raw database operations (CRUD)
    - Handles database-specific implementation details
    - Maps database results to domain models
    - Isolates database-specific code from business logic

    The repository should not contain business logic, validation, or data transformation.
    These concerns belong in the DataService layer.
    """

    def __init__(self, db_client: SupabaseClient) -> None:
        self.db_client = db_client
        logger.debug("Initialized data repo")

    # Content operations
    @supabase_operation
    async def save_datasource(self, data_source: DataSource) -> None:
        """Saves datasource record to the database."""
        data = data_source.model_dump(mode="json")
        logger.debug(f"Preparing to save source data: {data}")

        client = await self.db_client.get_client()
        result = await client.schema("content").table("data_sources").insert(data).execute()
        logger.info(f"Successfully saved source {result.data[0]}")

    @supabase_operation
    async def update_datasource(self, source: DataSource) -> None:
        """Updates datasource record in the database."""
        data = source.model_dump(mode="json")

        client = await self.db_client.get_client()

        await client.schema("content").table("data_sources").update(data).eq("source_id", source.source_id).execute()

    @supabase_operation
    async def retrieve_datasource(self, source_id: UUID) -> DataSource:
        """Retrieves datasource object from the database."""
        client = await self.db_client.get_client()
        result = await client.schema("content").table("data_sources").select("*").eq("source_id", source_id).execute()

        if not result.data:
            raise KeyError(f"Source {source_id} not found")

        return DataSource(**result.data[0])

    @supabase_operation
    async def list_datasources(self) -> list[DataSource]:
        """List all datasources."""
        client = await self.db_client.get_client()
        result = await client.schema("content").table("data_sources").select("*").execute()
        return [DataSource(**item) for item in result.data]

    # User request operations
    @supabase_operation
    async def save_user_request(self, request: AddContentSourceRequest) -> None:
        """Saves user request to the database."""
        data = request.model_dump(mode="json")
        logger.debug(f"Preparing data for database: {data}")

        client = await self.db_client.get_client()
        result = await client.schema("content").table("user_requests").insert(data).execute()
        logger.debug(f"Returned the result: {result.data}")

    @supabase_operation
    async def save_job(self, job: Job) -> None:
        """Creates a new job entry in the database."""
        data = job.model_dump(mode="json")
        logger.debug(f"Saving job data: {data}")

        client = await self.db_client.get_client()
        result = await client.schema("infra").table("jobs").insert(data).execute()
        logger.debug(f"Job saved with response: {result.data}")
        logger.info(f"Job {job.job_id} saved successfully")

    @supabase_operation
    async def update_job(self, job: Job) -> None:
        """Updates existing job in the database."""
        data = job.model_dump(mode="json")
        logger.debug(f"Updating job {job.job_id} with data: {data}")

        client = await self.db_client.get_client()
        result = await client.schema("infra").table("jobs").update(data).eq("job_id", str(job.job_id)).execute()
        logger.debug(f"Job updated with response: {result.data}")
        logger.info(f"Job {job.job_id} updated successfully")

    @supabase_operation
    async def retrieve_job(self, job_id: UUID) -> Job:
        """Retrieves a job from the database."""
        logger.debug(f"Retrieving job {job_id}")

        client = await self.db_client.get_client()
        result = await client.schema("infra").table("jobs").select("*").eq("job_id", str(job_id)).execute()

        if not result.data:
            raise JobNotFoundError(f"Job {job_id} not found")

        return Job.model_validate(result.data[0])

    @supabase_operation
    async def get_job_by_firecrawl_id(self, firecrawl_id: str) -> Job:
        """Retrieves a job by its FireCrawl ID."""
        logger.debug(f"Retrieving job with FireCrawl ID {firecrawl_id}")

        client = await self.db_client.get_client()
        result = await client.schema("infra").table("jobs").select("*").eq("firecrawl_id", firecrawl_id).execute()

        if not result.data:
            raise JobNotFoundError(f"No job found for FireCrawl ID: {firecrawl_id}")

        return Job.model_validate(result.data[0])

    @supabase_operation
    async def list_jobs(self, source_id: UUID | None = None) -> list[Job]:
        """Lists all jobs, optionally filtered by source_id."""
        client = await self.db_client.get_client()
        query = client.schema("infra").table("jobs").select("*")

        if source_id:
            query = query.eq("source_id", str(source_id))

        result = await query.execute()
        return [Job.model_validate(job_data) for job_data in result.data]

    # Content Operations
    async def save_crawl_result(self, crawl_result: CrawlResult) -> None:
        """Persists crawl results in the database."""
        pass

    async def get_latest_crawl_result(self, source_id: UUID) -> CrawlResult:
        """Retrieve the most recent crawl result for a source."""
        raise NotImplementedError("get_latest_crawl_result is not implemented yet")

    async def batch_save_results(self, results: list[CrawlResult]) -> None:
        """Save multiple crawl results in a single operation."""
        pass
