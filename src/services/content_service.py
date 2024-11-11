from datetime import UTC, datetime
from uuid import UUID

from src.api.v0.schemas.sources_schemas import (
    AddContentSourceRequest,
    SourceAPIResponse,
)
from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, WebhookEvent
from src.core._exceptions import JobNotFoundError
from src.core.content.crawler.crawler import FireCrawler
from src.core.system.job_manager import JobManager
from src.infrastructure.common.decorators import base_error_handler
from src.infrastructure.config.logger import get_logger
from src.models.common.jobs import CrawlJob, CrawlJobStatus
from src.models.content.content_source_models import Source, SourceStatus
from src.models.content.firecrawl_models import CrawlRequest, CrawlResult

logger = get_logger()


class ContentService:
    """Service for managing content sources."""

    def __init__(self, crawler: FireCrawler, job_manager: JobManager):
        self.crawler = crawler
        self.job_manager = job_manager
        self._sources: dict[str, Source] = {}  # In-memory storage for now

    async def add_source(self, request: AddContentSourceRequest) -> SourceAPIResponse:
        """Add a new content source and initiate crawling.

        Args:
            request: Validated request containing source configuration

        Returns:
            SourceAPIResponse: API response with source details

        Raises:
            CrawlerError: If crawler fails to start
        """
        try:
            # 1. Create Source with Pending state
            source = await self._persist_source(request=request)
            source.status = SourceStatus.PENDING  # Initial status
            self._sources[str(source.source_id)] = source

            # 2. Create CrawlRequest
            crawl_request = await self._create_crawl_request(request)

            # 3. Create Job
            job = await self.job_manager.create_job(
                source_id=source.source_id,  # for tracking later
                start_url=crawl_request.url,
            )
            source.job_id = job.job_id
            self._sources[str(source.source_id)] = source  # Update source in local storage

            # 3. Start the crawl

            response = await self.crawler.start_crawl(request=crawl_request)

            # 4. Update Source to CRAWLING (Firecrawl has accepted the job)
            if response.success:
                # Update firecrawl job id
                job.firecrawl_id = response.job_id
                await self.job_manager.update_job(job)

                # Update source
                source.status = SourceStatus.CRAWLING
                source.updated_at = datetime.now(UTC)
                self._sources[str(source.source_id)] = source  # Update source in local storage

            return SourceAPIResponse.from_source(source)

        except Exception as e:
            # Update source status to FAILED
            source.status = SourceStatus.FAILED
            source.updated_at = datetime.now(UTC)
            source.data = {**source.data, "error": str(e)}  # Store error in source data
            logger.error(f"Failed to create crawl job with source id {source.source_id}: {str(e)}")
            raise

    async def _persist_source(self, request: AddContentSourceRequest) -> Source:
        """Create a new content source and crawl request.

        Returns:
            tuple[Source, CrawlRequest]: Created source and crawl request
        """
        source = Source(
            source_type=request.source_type,
            data=request.model_dump(),
            status=SourceStatus.PENDING,
            job_id=None,  # Explicitly set as None initially
        )
        return source

    async def _create_crawl_request(self, request: AddContentSourceRequest) -> CrawlRequest:
        crawl_request = CrawlRequest(**request.config.model_dump())
        return crawl_request

    async def update_source_status(self, source_id: UUID, status: SourceStatus) -> Source:
        """Update source status.

        Args:
            source_id: Source UUID
            status: New status

        Returns:
            Source: Updated source

        Raises:
            KeyError: If source not found
        """
        source = self._sources[str(source_id)]
        source.status = status
        source.updated_at = datetime.now(UTC)
        return source

    async def list_sources(self) -> list[SourceAPIResponse]:
        """List all content sources."""
        return [SourceAPIResponse.from_source(source) for source in self._sources.values()]

    async def get_source(self, source_id: str) -> SourceAPIResponse:
        """Get a source by ID."""
        source = self._sources.get(source_id)
        if not source:
            raise KeyError(f"Source {source_id} not found")
        return SourceAPIResponse.from_source(source)

    async def handle_event(self, event: WebhookEvent) -> None:
        """Handles webhook events related to content ingestion."""
        try:
            logger.info(f"Received webhook event: {event.data.event_type} for FireCrawl job " f"{event.data.crawl_id}")
            logger.debug(f"Event data: {event.data.model_dump()}")

            # Get job by FireCrawl ID
            job = await self.job_manager.get_job_by_firecrawl_id(event.data.crawl_id)

            # Identify provider
            if event.provider == "firecrawl":
                if not event.data.success:
                    logger.error(f"Event failed: {event.data.error}")
                    await self._handle_failure(event)
                    return

                match event.data.event_type:
                    case FireCrawlEventType.CRAWL_STARTED:
                        logger.info(f"Crawl started for job {job.job_id}")
                        await self._handle_started(job)

                    case FireCrawlEventType.CRAWL_PAGE:
                        logger.info(f"Page crawled for job {job.job_id}")
                        await self._handle_page_crawled(job)

                    case FireCrawlEventType.CRAWL_COMPLETED:
                        logger.info(f"Crawl completed for job {job.job_id}")
                        await self._handle_completed(job)

                    case FireCrawlEventType.CRAWL_FAILED:
                        logger.error(f"Crawl failed for job {job.job_id}: {event.error}")
                        await self._handle_failure(job, event.error or "Unknown error")

        except JobNotFoundError as e:
            logger.error(f"Job not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unhandled error in webhook handler: {str(e)}", exc_info=True)
            if "job" in locals():
                await self._handle_failure(job, f"Internal error: {str(e)}")
            raise

    @base_error_handler
    async def _handle_started(self, job: CrawlJob) -> None:
        """Handle crawl.started event"""
        # Update job
        job.status = CrawlJobStatus.IN_PROGRESS

        # Update Source

        # Do other logic

        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_page_crawled(self, job: CrawlJob) -> None:
        """Handle crawl.page event - increment page count"""
        job.pages_crawled += 1
        logger.debug(f"Pages crawled: {job.pages_crawled}")
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_completed(self, job: CrawlJob) -> None:
        """Handle crawl.completed event"""
        # Update job data

        job.status = CrawlJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.pages_crawled = job.pages_crawled  # Set total pages to what we've crawled

        # Retrieve the results
        results = await self._get_crawl_results(job=job)

        # Update source record
        # self.update_source_status()

        await self.job_manager.update_job(job)

        logger.info("Printing results for now")
        return results

    @base_error_handler
    async def _handle_failure(self, job: CrawlJob, error: str) -> None:
        """Handle crawl.failed event"""
        job.status = CrawlJobStatus.FAILED
        job.error = error
        job.completed_at = datetime.now(UTC)
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _get_crawl_results(self, job: CrawlJob) -> CrawlResult:
        results = await self.crawler.get_results(crawl_job=job)
        return results
