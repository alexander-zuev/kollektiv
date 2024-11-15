from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.api.v0.schemas.sources_schemas import (
    AddContentSourceRequest,
    SourceAPIResponse,
)
from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent
from src.core._exceptions import DataSourceError, JobNotFoundError
from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.infrastructure.common.decorators import base_error_handler, generic_error_handler
from src.infrastructure.config.logger import get_logger
from src.models.common.jobs import CrawlJob, JobStatus
from src.models.content.content_source_models import DataSource, SourceStatus
from src.models.content.firecrawl_models import CrawlRequest, CrawlResult
from src.services.data_service import DataService

logger = get_logger()


class ContentService:
    """Service for managing content sources."""

    def __init__(self, crawler: FireCrawler, job_manager: JobManager, data_service: DataService):
        self.crawler = crawler
        self.job_manager = job_manager
        self.data_service = data_service

    @generic_error_handler
    async def add_source(self, request: AddContentSourceRequest) -> SourceAPIResponse:
        """Add a new content source and initiate crawling.

        Args:
            request: Validated request containing source configuration

        Returns:
            SourceAPIResponse: API response with source details

        Raises:
            CrawlerError: If crawler fails to start
        """
        data_source = None  # Initialize to None
        try:
            logger.info(f"Starting to add source for request {request.request_id}")

            # 1. Save user request

            await self._save_user_request(request=request)
            logger.debug("STEP 1 USER REQUEST SAVED")

            # 2. Save datasource entry
            data_source = await self._save_datasource(request=request)
            logger.debug("STEP 2 DATA SOURCE SAVED")

            # 3. Create CrawlRequest
            crawl_request = await self._create_crawl_request(request)
            logger.debug("STEP 3 Crawl Request created")

            # 4. Create Job
            job = await self.job_manager.create_job(
                source_id=data_source.source_id,
                start_url=crawl_request.url,
            )
            logger.debug("STEP 4 Job saved")

            # 5. Update source with job_id
            data_source = await self.update_source(source_id=data_source.source_id, updates={"job_id": job.job_id})
            logger.debug("STEP 5 Source linked to the job")

            # 6. Start the crawl
            response = await self.crawler.start_crawl(request=crawl_request)
            logger.debug("STEP 6 Crawl started")

            # 7. If crawl started successfully, update source and job
            if response.success:
                # Update job with firecrawl_id
                job.firecrawl_id = response.job_id
                await self.job_manager.update_job(job)
                logger.debug("STEP 7 Job completed")

                # Update source status to CRAWLING
                data_source = await self.update_source(
                    source_id=data_source.source_id,
                    updates={"status": SourceStatus.CRAWLING, "updated_at": datetime.now(UTC)},
                )
                logger.debug("STEP 7 Source updated")

            return SourceAPIResponse.from_source(data_source)

        except DataSourceError as e:
            # Update source status to FAILED if it exists
            if data_source:
                await self.update_source(
                    source_id=data_source.source_id, updates={"status": SourceStatus.FAILED, "error": str(e)}
                )
            logger.error(f"Failed to save data source: {e}", exc_info=True)
            raise

    async def _save_datasource(self, request: AddContentSourceRequest) -> DataSource:
        """Initiates saving of the datasource record into the database."""
        data_source = DataSource(
            source_type=request.source_type,
            status=SourceStatus.PENDING,
            metadata=request.request_config.model_dump(),
            request_id=request.request_id,
        )

        await self.data_service.save_datasource(data_source=data_source)
        logger.info(f"Data source {data_source.source_id} created successfully")

        return data_source

    async def _save_user_request(self, request: AddContentSourceRequest) -> None:
        logger.debug(f"Saving user request {request.model_dump()}")
        await self.data_service.save_user_request(request=request)
        logger.info(f"User request {request.request_id} saved successfully")

    async def update_source(self, source_id: UUID, updates: dict[str, Any]) -> DataSource:
        """Update source with arbitrary field updates.

        Args:
            source_id: Source to update
            updates: Dictionary of field updates {field_name: new_value}

        Returns:
            DataSource: Updated source
        """
        logger.debug(f"Updating source {source_id} with updates: {updates}")
        updates["updated_at"] = datetime.now(UTC)
        updated_source = await self.data_service.update_datasource(source_id, updates)
        logger.info(f"Successfully updated source {source_id}")
        return DataSource.model_validate(updated_source)

    async def _create_crawl_request(self, request: AddContentSourceRequest) -> CrawlRequest:
        crawl_request = CrawlRequest(**request.request_config.model_dump())
        return crawl_request

    async def list_sources(self) -> list[SourceAPIResponse]:
        """List all content sources."""
        sources = await self.data_service.list_datasources()
        return [SourceAPIResponse.from_source(source) for source in sources]

    async def get_source(self, source_id: UUID) -> SourceAPIResponse:
        """Get a source by UUID."""
        source = await self.data_service.retrieve_datasource(source_id=source_id)
        return SourceAPIResponse.from_source(source)

    @base_error_handler
    async def handle_event(self, event: FireCrawlWebhookEvent) -> None:
        """Handles webhook events related to content ingestion."""
        try:
            logger.info(f"Received webhook event: {event.data.event_type} for FireCrawl job {event.data.crawl_id}")

            # Get job by FireCrawl ID
            job = await self.job_manager.get_job_by_firecrawl_id(event.data.crawl_id)
            if not job:
                raise JobNotFoundError(event.data.crawl_id)

            # Identify provider
            if event.provider == event.provider.FIRECRAWL:
                if not event.data.success:
                    await self._handle_failure(job, event.error or "Unknown error")
                    return

                match event.data.event_type:
                    case FireCrawlEventType.CRAWL_STARTED:
                        logger.info(f"Crawl started for job {job.job_id}")
                        await self._handle_started(job)

                    case FireCrawlEventType.CRAWL_PAGE:
                        logger.info(f"Page crawled for job {job.job_id}")
                        await self._handle_page_crawled(job=job, event=event)

                    case FireCrawlEventType.CRAWL_COMPLETED:
                        logger.info(f"Crawl completed for job {job.job_id}")
                        await self._handle_completed(job)
                        return

                    case FireCrawlEventType.CRAWL_FAILED:
                        logger.error(f"Crawl failed for job {job.job_id}: {event.error}")
                        await self._handle_failure(job, event.error or "Unknown error")

        except JobNotFoundError as e:
            logger.error(f"Job not found for FireCrawl ID {event.data.crawl_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error handling webhook event {event.data.event_type}: {e}", exc_info=True)
            raise

    @base_error_handler
    async def _handle_started(self, job: CrawlJob) -> None:
        """Handle crawl.started event"""
        # Update job
        job.status = JobStatus.IN_PROGRESS
        await self.job_manager.update_job(job)

        # Update Source
        await self.update_source(source_id=job.source_id, updates={"status": SourceStatus.CRAWLING})

    @base_error_handler
    async def _handle_page_crawled(self, job: CrawlJob, event: FireCrawlWebhookEvent) -> None:
        """Handle crawl.page event - increment page count"""
        # Update job count
        job.pages_crawled += 1
        logger.debug(f"Pages crawled: {job.pages_crawled}")
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_completed(self, job: CrawlJob) -> None:
        """Handle crawl.completed event"""
        try:
            # Update job data
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)

            # Retrieve and process results
            results = await self._get_crawl_results(job=job)

            # Update job record
            await self.job_manager.update_job(job)

            # Store results
            await self.data_service.save_crawl_result(results)

            logger.info(f"Completed processing job {job.job_id}")
        except Exception as e:
            logger.error(f"Failed to handle completion for job {job.job_id}: {e}")
            await self._handle_failure(job, str(e))
            raise

    @base_error_handler
    async def _handle_failure(self, job: CrawlJob, error: str) -> None:
        """Handle crawl.failed event"""
        # Update job
        job.status = JobStatus.FAILED
        job.error = error
        job.completed_at = datetime.now(UTC)
        await self.job_manager.update_job(job=job)

        # Update source
        await self.update_source(source_id=job.source_id, updates={"status": SourceStatus.FAILED})

    @base_error_handler
    async def _get_crawl_results(self, job: CrawlJob) -> CrawlResult:
        """Get crawl results and validate them."""
        crawl_result = await self.crawler.get_results(crawl_job=job)
        return CrawlResult.model_validate(crawl_result)
