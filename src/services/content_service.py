from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.api.v0.schemas.sources_schemas import (
    AddContentSourceRequest,
    SourceAPIResponse,
)
from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent, WebhookProvider
from src.core._exceptions import DataSourceError, JobNotFoundError
from src.core.content.crawler import FireCrawler
from src.infra.decorators import generic_error_handler
from src.infra.logger import get_logger
from src.infra.rq.rq_manager import RQManager
from src.infra.rq.tasks import process_documents_job
from src.models.content_models import DataSource, Document, SourceStatus
from src.models.firecrawl_models import CrawlRequest
from src.models.job_models import Job, JobStatus, JobType
from src.services.data_service import DataService
from src.services.job_manager import JobManager

logger = get_logger()


class ContentService:
    """Service for managing content sources."""

    def __init__(
        self,
        crawler: FireCrawler,
        job_manager: JobManager,
        data_service: DataService,
        rq_manager: RQManager,
    ):
        self.crawler = crawler
        self.job_manager = job_manager
        self.data_service = data_service
        self.rq_manager = rq_manager

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
        # TODO: ensure this uses a transaction with context manager
        # TODO: refactor into smaller items so that I can remove one large try-except from here
        data_source = None  # Initialize to None
        try:
            logger.info(f"Starting to add source for request {request.request_id}")

            # 1. Save user request
            await self._save_user_request(request=request)
            logger.debug("STEP 1 User request saved")

            # 2. Save datasource entry
            data_source = await self._create_and_save_datasource(request=request)
            logger.debug("STEP 2 Data source created")

            # 3. Create CrawlRequest
            crawl_request = await self._create_crawl_request(request)
            logger.debug("STEP 3 Crawl Request created")

            # 4. Create Job
            job = await self.job_manager.create_job(
                job_type=JobType.CRAWL,
                source_id=data_source.source_id,
                url=request.request_config.url,
            )
            logger.debug("STEP 4 Job saved")

            # 5. Update source with job_id
            data_source = await self.data_service.update_datasource(
                source_id=data_source.source_id, updates={"job_id": job.job_id}
            )
            logger.debug("STEP 5 Source linked to the job")

            # 6. Start the crawl
            response = await self.crawler.start_crawl(request=crawl_request)
            logger.debug("STEP 6 Crawl started")

            # 7. If crawl started successfully, update source and job
            if response.success:
                # Update job with firecrawl_id
                await self.job_manager.update_job(
                    job_id=job.job_id,
                    updates={"details": {"firecrawl_id": response.job_id}, "status": JobStatus.IN_PROGRESS},
                )
                logger.debug("STEP 7 Job started")

                # Update source status to CRAWLING
                data_source = await self.data_service.update_datasource(
                    source_id=data_source.source_id,
                    updates={"status": SourceStatus.CRAWLING, "updated_at": datetime.now(UTC)},
                )
                logger.debug("STEP 8 Source updated")

            if data_source is None:
                raise DataSourceError(data_source.source_id, message="Data source creation failed.")

            return SourceAPIResponse.from_source(data_source)

        except DataSourceError as e:
            # Update source status to FAILED if it exists
            if data_source:
                await self.data_service.update_datasource(
                    source_id=data_source.source_id, updates={"status": SourceStatus.FAILED, "error": str(e)}
                )
            logger.error(f"Failed to save data source: {e}", exc_info=True)
            raise

    async def _create_and_save_datasource(self, request: AddContentSourceRequest) -> DataSource:
        """Initiates saving of the datasource record into the database."""
        data_source = DataSource(
            user_id=request.user_id,
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

    @generic_error_handler
    async def handle_event(self, event: FireCrawlWebhookEvent) -> None:
        """Handles webhook events related to content ingestion."""
        logger.info(
            "Processing webhook event",
            extra={
                "event_type": event.data.event_type,
                "firecrawl_id": event.data.firecrawl_id,
                "provider": event.provider,
            },
        )

        try:
            job = await self.job_manager.get_by_firecrawl_id(event.data.firecrawl_id)

            if event.provider == WebhookProvider.FIRECRAWL:
                match event.data.event_type:
                    case FireCrawlEventType.CRAWL_STARTED:
                        await self._handle_started(job)

                    case FireCrawlEventType.CRAWL_PAGE:
                        await self._handle_page_crawled(job=job, event=event)

                    case FireCrawlEventType.CRAWL_COMPLETED:
                        await self._handle_crawl_completed(job)

                    case FireCrawlEventType.CRAWL_FAILED:
                        await self._handle_failure(job, event.data.error or "Unknown error")

        except JobNotFoundError:
            logger.error("Job not found", extra={"firecrawl_id": event.data.firecrawl_id})
            raise
        except Exception as e:
            logger.error(
                "Event handling failed",
                extra={"event_type": event.data.event_type, "job_id": job.job_id if job else None, "error": str(e)},
            )
            raise

    @generic_error_handler
    async def _handle_started(self, job: Job) -> None:
        """Handle crawl.started event"""
        try:
            # Update job status
            await self.job_manager.update_job(
                job_id=job.job_id, updates={"status": JobStatus.IN_PROGRESS, "started_at": datetime.now(UTC)}
            )
            logger.debug(f"Updated job {job.job_id} status to IN_PROGRESS")

            # Update source
            await self.data_service.update_datasource(
                source_id=job.details.source_id,
                updates={"status": SourceStatus.CRAWLING, "updated_at": datetime.now(UTC)},
            )
            logger.debug(f"Updated source {job.details.source_id} status to CRAWLING")
        except Exception as e:
            logger.error(f"Failed to handle start event for job {job.job_id}: {e}")
            await self._handle_failure(job, str(e))
            raise

    async def _handle_page_crawled(self, job: Job, event: FireCrawlWebhookEvent) -> None:
        """Handle crawl.page event - increment page count"""
        try:
            # Simply increment pages_crawled
            await self.job_manager.update_job(
                job_id=job.job_id, updates={"details": {"pages_crawled": job.details.pages_crawled + 1}}
            )
            logger.debug(f"Updated job {job.job_id} pages_crawled to {job.details.pages_crawled + 1}")
        except Exception as e:
            logger.error("Failed to update page count", extra={"job_id": job.job_id, "error": str(e)})
            raise

    # TODO: de-couple and move to job management via Redis. It should just enqueu the processing job instead of
    # handling it itself.
    @generic_error_handler
    async def _handle_crawl_completed(self, job: Job) -> None:
        """Handle crawl.completed event"""
        if job.job_type != JobType.CRAWL:
            raise ValueError(f"Expected CRAWL job type, got {job.job_type}")

        details = job.details  # This is a CrawlJobDetails instance

        # 1. Get documents
        documents = await self.crawler.get_results(
            firecrawl_id=details.firecrawl_id,  # Access as property, not dict
            source_id=details.source_id,  # Access as property, not dict
        )

        # 2. Save documents into db and collect their IDs
        saved_documents = await self.data_service.save_documents(documents=documents)
        document_ids = [doc.document_id for doc in saved_documents]  # Collect document IDs
        logger.debug(f"Successfully saved {len(document_ids)} documents for job {job.job_id}")

        # 3. Update source entty
        crawl_metadata = await self._create_source_metadata(documents=documents)
        await self.data_service.update_datasource(
            source_id=details.source_id,
            updates={
                "status": SourceStatus.CRAWLED,
                "metadata": crawl_metadata,
            },
        )

        # 4. complete the job
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={
                "status": JobStatus.COMPLETED,
                "completed_at": datetime.now(UTC),
            },
        )
        logger.debug(f"Updated job {job.job_id} status to COMPLETED")

        # 5. Create a new processing job
        processing_job = await self.job_manager.create_job(
            job_type=JobType.PROCESS,
            source_id=details.source_id,  # Fix: access as property
            details={"document_ids": document_ids},
        )

        # 6. Update source status
        await self.data_service.update_datasource(
            source_id=details.source_id,  # Fix: access as property
            updates={"status": SourceStatus.PROCESSING, "job_id": processing_job.job_id},
        )
        logger.debug(f"Updated source {details.source_id} status to PROCESSING")

        # 7. Enqueu processing job
        await self.rq_manager.enqueue_job(job=process_documents_job, args=(processing_job.job_id, document_ids))
        logger.debug(f"Enqueued processing job {processing_job.job_id}")

    async def handle_processing_job(self, message: dict) -> None:
        """Handles a process documents jobs."""
        # 1. Retrieve job by job_id
        job = await self.job_manager.get_by_id(message["job_id"])

        # 2. Handle event
        match job.status:
            case JobStatus.COMPLETED:
                logger.info(f"Processing job {job.job_id} completed")
                await self.handle_completed_processing_job(job)
            case JobStatus.FAILED:
                logger.error(f"Processing job {job.job_id} failed")
                await self.handle_failed_processing_job(job, job.error)

    async def handle_completed_processing_job(self, job: Job) -> None:
        """Completes the ingestion process by updating the source and returning the source metadata."""
        source_id = job.details.source_id

        # 1. Update source status
        await self.data_service.update_datasource(
            source_id=source_id,
            updates={"status": SourceStatus.ADDING_SUMMARY, "updated_at": datetime.now(UTC)},
        )

        # 2. Update job status
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={"status": JobStatus.COMPLETED, "completed_at": datetime.now(UTC)},
        )

        # 3. Generate source summary
        # await self.assistant.generate_source_summary(source_id=source_id)

        # 4. After all said and done
        await self.data_service.update_datasource(
            source_id=source_id,
            updates={"status": SourceStatus.COMPLETED, "updated_at": datetime.now(UTC)},
        )

        # 5. Inform the client
        # TODO: implement

    async def handle_failed_processing_job(self, job: Job, error: str) -> None:
        """Handles a failed processing job."""
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={"status": JobStatus.FAILED, "completed_at": datetime.now(UTC), "error": error},
        )

        # retry potentially? or just inform the user

    async def _create_source_metadata(self, documents: list[Document]) -> dict[str, Any]:
        """Create updated source metadata after crawl completion.

        Args:
            documents: List of saved documents

        Returns:
            Updated metadata dictionary
        """
        # Extract unique links from document metadata
        unique_links = set()
        for doc in documents:
            if source_url := doc.metadata.get("source_url"):
                unique_links.add(source_url)

        # Create updated metadata
        return {
            "total_pages": len(documents),
            "unique_links": list(unique_links),
        }

    @generic_error_handler
    async def _handle_failure(self, job: Job, error: str) -> None:
        """Handle crawl.failed event"""
        try:
            # Update job with error
            await self.job_manager.update_job(
                job_id=job.job_id,
                updates={"status": JobStatus.FAILED, "completed_at": datetime.now(UTC), "error": error},
            )
            logger.debug(f"Updated job {job.job_id} status to FAILED")

            # Update source status
            source_id = (
                job.details.source_id  # This works because both CrawlJobDetails and ProcessingJobDetails have source_id
            )
            await self.data_service.update_datasource(
                source_id=source_id,
                updates={"status": SourceStatus.FAILED, "error": error, "updated_at": datetime.now(UTC)},
            )
            logger.debug(f"Updated source {source_id} status to FAILED")
        except Exception as e:
            logger.error(f"Failed to handle failure for job {job.job_id}: {e}", exc_info=True)
            raise
