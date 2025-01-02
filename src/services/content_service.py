import asyncio
from datetime import UTC, datetime
from uuid import UUID

from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent, WebhookProvider
from src.core._exceptions import JobNotFoundError
from src.core.content.crawler import FireCrawler
from src.infra.celery.tasks import process_documents
from src.infra.decorators import generic_error_handler
from src.infra.logger import get_logger
from src.models.content_models import (
    AddContentSourceRequest,
    DataSource,
    FireCrawlSourceMetadata,
    SourceAPIResponse,
    SourceStatus,
)
from src.models.firecrawl_models import CrawlRequest
from src.models.job_models import CrawlJobDetails, Job, JobStatus, JobType, ProcessingJobDetails
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
    ):
        self.crawler = crawler
        self.job_manager = job_manager
        self.data_service = data_service

    @generic_error_handler
    async def add_source(self, request: AddContentSourceRequest) -> SourceAPIResponse:
        """POST /sources entrypoint.

        Args:
            request: Validated request containing source configuration

        Returns:
            SourceAPIResponse: API response with source details

        Raises:
            CrawlerError: If crawler fails to start
        """
        data_source = None
        job = None
        try:
            logger.info(f"Starting to add source for request {request.request_id}")

            # Send a crawl request to firecrawl
            crawl_request = self._create_crawl_request(request)
            response = await self.crawler.start_crawl(request=crawl_request)
            logger.debug("STEP 1. Crawl started")

            if not response.success:
                logger.debug("STEP 2. Crawl failed")
                return SourceAPIResponse(
                    source_id=data_source.source_id,
                    source_type=data_source.source_type,
                    status=SourceStatus.FAILED,
                    created_at=data_source.created_at,
                    error="Failed to start a crawl, please try again.",
                )

            logger.debug("STEP 3. Crawl started successfully")

            # 2. Only if crawl started successfully, create DB entries
            await self._save_user_request(request)
            data_source = await self._create_and_save_datasource(request)

            # 3. Create and link job with firecrawl_id
            job = await self.job_manager.create_job(
                job_type=JobType.CRAWL,
                details=CrawlJobDetails(
                    source_id=data_source.source_id,
                    url=request.request_config.url,
                    firecrawl_id=response.job_id,
                ),
            )

            # 4. Update source with job_id and status
            await self.data_service.update_datasource(
                source_id=data_source.source_id,
                updates={
                    "status": SourceStatus.CRAWLING,
                    "job_id": job.job_id,
                },
            )
            return SourceAPIResponse.from_source(data_source)
        except Exception as e:
            logger.exception(f"Failed to add source: {e}")
            if data_source:
                await self.data_service.update_datasource(
                    source_id=data_source.source_id,
                    updates={"status": SourceStatus.FAILED, "error": str(e)},
                )
            if job:
                await self.job_manager.update_job(
                    job_id=job.job_id, updates={"status": JobStatus.FAILED, "error": str(e)}
                )
            return SourceAPIResponse(
                source_id=data_source.source_id,
                source_type=data_source.source_type,
                status=SourceStatus.FAILED,
                created_at=data_source.created_at,
                error=str(e),
            )

    async def _create_and_save_datasource(self, request: AddContentSourceRequest) -> DataSource:
        """Initiates saving of the datasource record into the database."""
        data_source = DataSource(
            user_id=request.user_id,
            source_type=request.source_type,
            status=SourceStatus.PENDING,
            metadata=FireCrawlSourceMetadata(
                crawl_config=request.request_config,
                total_pages=0,
            ),
            request_id=request.request_id,
        )

        await self.data_service.save_datasource(data_source=data_source)
        logger.info(f"Data source {data_source.source_id} created successfully")

        return data_source

    async def _save_user_request(self, request: AddContentSourceRequest) -> None:
        logger.debug(f"Saving user request {request.model_dump()}")
        await self.data_service.save_user_request(request=request)
        logger.info(f"User request {request.request_id} saved successfully")

    def _create_crawl_request(self, request: AddContentSourceRequest) -> CrawlRequest:
        crawl_request = CrawlRequest(**request.request_config.model_dump())
        return crawl_request

    async def list_sources(self) -> list[SourceAPIResponse]:
        """GET /sources entrypoint"""
        sources = await self.data_service.list_datasources()
        return [SourceAPIResponse.from_source(source) for source in sources]

    async def get_source(self, source_id: UUID) -> SourceAPIResponse:
        """GET /sources/{source_id} entrypoint"""
        source = await self.data_service.retrieve_datasource(source_id=source_id)
        return SourceAPIResponse.from_source(source)

    async def handle_webhook_event(self, event: FireCrawlWebhookEvent) -> None:
        """Handles webhook events related to content ingestion."""
        logger.info(
            "Processing webhook event",
            {
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
            logger.exception("Job not found", {"firecrawl_id": event.data.firecrawl_id})
            raise
        except Exception as e:
            logger.exception(
                "Firecrawl webhook event handling failed",
                {"event_type": event.data.event_type, "job_id": job.job_id if job else None, "error": str(e)},
            )
            raise

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
            await self.job_manager.update_job(
                job_id=job.job_id, updates={"details": {"pages_crawled": job.details.pages_crawled + 1}}
            )
            logger.debug(f"Updated job {job.job_id} pages_crawled to {job.details.pages_crawled + 1}")
        except Exception as e:
            logger.error("Failed to update page count", {"job_id": job.job_id, "error": str(e)})
            raise

    async def _handle_crawl_completed(self, job: Job) -> None:
        """Handle crawl.completed event"""
        # 1. Get source & documents
        documents, source = await asyncio.gather(
            self.crawler.get_results(
                firecrawl_id=job.details.firecrawl_id,
                source_id=job.details.source_id,
            ),
            self.data_service.get_datasource(job.details.source_id),
        )

        # 2. Enqueue processing job
        result = process_documents.delay(
            [document.model_dump(mode="json", serialize_as_any=True) for document in documents],
            user_id=str(source.user_id),
        )
        logger.info(f"Processing job in celery {result.task_id} enqueued")

        # 3. Update source, jobs, and save documents
        saved_documents, _, processing_job = await asyncio.gather(
            self.data_service.save_documents(documents=documents),
            self.job_manager.update_job(
                job_id=job.job_id,
                updates={"status": JobStatus.COMPLETED, "completed_at": datetime.now(UTC)},
            ),
            self.job_manager.create_job(
                job_type=JobType.PROCESSING,
                details=ProcessingJobDetails(
                    document_ids=[document.document_id for document in documents],
                    source_id=source.source_id,
                ),
            ),
        )
        logger.debug(f"Updated job {job.job_id} status to COMPLETED")

        # 4.  Update source
        await self.data_service.update_datasource(
            source_id=source.source_id,
            updates={
                "metadata": FireCrawlSourceMetadata(
                    crawl_config=source.metadata.crawl_config,  # Keep existing
                    total_pages=len(documents),  # Update this
                ),
                "status": SourceStatus.PROCESSING,
                "job_id": processing_job.job_id,
                "updated_at": datetime.now(UTC),
            },
        )
        logger.debug(f"Updated source {source.source_id} status to PROCESSING")

    async def handle_pubsub_event(self, message: dict) -> None:
        """Handles a process documents jobs."""
        # 1. Retrieve job by job_id
        job = await self.data_service.get_job(UUID(message["job_id"]))

        # 2. Handle event
        match job.status:
            case JobStatus.COMPLETED:
                logger.info(f"Processing job {job.job_id} completed")
                await self.handle_completed_processing_job(job)
            case JobStatus.FAILED:
                error = message.get("error")
                logger.error(f"Processing job {job.job_id} failed")
                await self.handle_failed_processing_job(job, error)

    async def handle_completed_processing_job(self, job: Job) -> None:
        """Completes the ingestion process by updating the source and returning the source metadata."""
        # 1. Update source status
        await self.data_service.update_datasource(
            source_id=job.details.source_id,
            updates={"status": SourceStatus.ADDING_SUMMARY, "updated_at": datetime.now(UTC)},
        )

        # 2. Update job status
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={"status": JobStatus.COMPLETED, "completed_at": datetime.now(UTC)},
        )

        # 3. Generate source summary
        # await self.assistant.generate_source_summary(source_id=source_id)

        # 5. Inform the client
        logger.info(f"Source {source_id} completed!!!")

    async def handle_failed_processing_job(self, job: Job, error: str) -> None:
        """Handles a failed processing job."""
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={"status": JobStatus.FAILED, "completed_at": datetime.now(UTC), "error": error},
        )
        # TODO: retry potentially? or just inform the user

    async def _handle_failure(self, job: Job, error: str) -> None:
        """Handle crawl.failed event"""
        # Update job with error
        await self.job_manager.update_job(
            job_id=job.job_id,
            updates={"status": JobStatus.FAILED, "completed_at": datetime.now(UTC), "error": error},
        )
        logger.debug(f"Updated job {job.job_id} status to FAILED")

        # Update source status
        source_id = job.details.source_id
        await self.data_service.update_datasource(
            source_id=source_id,
            updates={"status": SourceStatus.FAILED, "error": error, "updated_at": datetime.now(UTC)},
        )
        logger.debug(f"Updated source {source_id} status to FAILED")
