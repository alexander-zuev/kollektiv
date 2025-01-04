import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent, WebhookProvider
from src.core._exceptions import CrawlerError, JobNotFoundError
from src.core.content.crawler import FireCrawler
from src.infra.celery.tasks import process_documents
from src.infra.decorators import generic_error_handler
from src.infra.events.channels import Channels
from src.infra.events.event_publisher import EventPublisher
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.models.content_models import (
    AddContentSourceRequest,
    AddContentSourceResponse,
    DataSource,
    FireCrawlSourceMetadata,
    ProcessingEvent,
    SourceEvent,
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
        redis_manager: RedisManager,
        event_publisher: EventPublisher,
    ):
        self.crawler = crawler
        self.job_manager = job_manager
        self.data_service = data_service
        self.redis_manager = redis_manager
        self.event_publisher = event_publisher

    @generic_error_handler
    async def add_source(self, request: AddContentSourceRequest) -> AddContentSourceResponse:
        """POST /sources entrypoint.

        Args:
            request: Validated request containing source configuration

        Returns:
            SourceAPIResponse: API response with source details

        Raises:
            CrawlerError: If crawler fails to start
        """
        source = None
        job = None
        try:
            logger.info(f"Starting to add source for request {request.request_id}")

            # Send a crawl request to firecrawl
            response = await self.crawler.start_crawl(request=CrawlRequest(**request.request_config.model_dump()))
            await self._save_user_request(request)
            source = await self._create_and_save_datasource(request)
            logger.debug("STEP 1. Crawl started")

            # Publish event
            await self._publish_source_event(
                source_id=source.source_id,
                status=source.status,
            )

            logger.debug("STEP 3. Crawl started successfully")

            # 3. Create and link job with firecrawl_id
            job = await self.job_manager.create_job(
                job_type=JobType.CRAWL,
                details=CrawlJobDetails(
                    source_id=source.source_id,
                    url=request.request_config.url,
                    firecrawl_id=response.job_id,
                ),
            )

            # 4. Update source with job_id and status
            updated_source = await self.data_service.update_datasource(
                source_id=source.source_id,
                updates={
                    "status": SourceStatus.CRAWLING,
                    "job_id": job.job_id,
                },
            )

            # 5. Publish crawling event
            await self._publish_source_event(
                source_id=updated_source.source_id,
                status=updated_source.status,
            )

            return AddContentSourceResponse.from_source(updated_source)
        except CrawlerError as e:
            # Crawler error -> returns a response
            logger.exception(f"Crawling of the source failed: {e}")
            return AddContentSourceResponse(
                source_id=source.source_id,
                status=SourceStatus.FAILED,
                error=str(e),
                error_type="crawler",
            )
        except Exception as e:
            # Infrastructure error -> returns a response
            logger.exception(f"Failed to add source: {e}")
            if source:
                await self.data_service.update_datasource(
                    source_id=source.source_id,
                    updates={"status": SourceStatus.FAILED, "error": str(e)},
                )
            if job:
                await self.job_manager.update_job(
                    job_id=job.job_id, updates={"status": JobStatus.FAILED, "error": str(e)}
                )

            # Publish failed event
            await self._publish_source_event(
                source_id=source.source_id,
                status=SourceStatus.FAILED,
            )

            return AddContentSourceResponse(
                source_id=source.source_id,
                status=SourceStatus.FAILED,
                error="An internal server error occured, we are working on it.",  # do not expose internal errors
                error_type="infrastructure",
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

    async def list_sources(self) -> list[AddContentSourceResponse]:
        """GET /sources entrypoint"""
        sources = await self.data_service.list_datasources()
        return [AddContentSourceResponse.from_source(source) for source in sources]

    async def get_source(self, source_id: UUID) -> AddContentSourceResponse:
        """GET /sources/{source_id} entrypoint"""
        source = await self.data_service.retrieve_datasource(source_id=source_id)
        return AddContentSourceResponse.from_source(source)

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
                        await self._handle_crawl_failure(job, event.data.error or "Unknown error")

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
            await self._handle_crawl_failure(job, str(e))
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
            source_id=str(source.source_id),
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

        # 4. Update source
        await asyncio.gather(
            self.data_service.update_datasource(
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
            ),
            self._publish_source_event(
                source_id=source.source_id,
                status=SourceStatus.PROCESSING,
            ),
        )

        logger.debug(f"Updated source {source.source_id} status to PROCESSING")

    async def handle_pubsub_event(self, message: ProcessingEvent) -> None:
        """Handles a process documents jobs."""
        # 1. Pass into completed or failed processing job
        match message.event_type:
            case "completed":
                await self.handle_completed_processing_job(message)
            case "failed":
                await self.handle_failed_processing_job(message)
            case _:
                logger.warning(f"Unknown event type: {message.event_type}")

    async def handle_completed_processing_job(self, message: ProcessingEvent) -> None:
        """Completes the ingestion process by updating the source and returning the source metadata."""
        logger.info(f"Source {message.source_id} completed!!!")
        await self._publish_source_event(
            source_id=message.source_id,
            status=SourceStatus.COMPLETED,
        )

    async def handle_failed_processing_job(self, message: ProcessingEvent) -> None:
        """Handles a failed processing job."""
        logger.info(f"Source {message.source_id} failed!")
        await self._publish_source_event(
            source_id=message.source_id,
            status=SourceStatus.FAILED,
            error=message.error,
        )

    async def _handle_crawl_failure(self, job: Job, error: str) -> None:
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

        await self._publish_source_event(
            source_id=source_id,
            status=SourceStatus.FAILED,
            error=error,
        )

    async def stream_source_events(
        self,
        source_id: UUID,
    ) -> AsyncGenerator[SourceEvent, None]:
        """Stream SSE events for a source."""
        try:
            source = await self.data_service.get_datasource(source_id)
            yield SourceEvent(
                source_id=source.source_id,
                status=source.status,
                metadata={},
            )
            logger.info(f"Streamed source {source_id} event {source.status}")

            # Get async client
            redis_client = await self.redis_manager.get_async_client()
            async with redis_client.pubsub() as pubsub:
                await pubsub.subscribe(Channels.Sources.events(source_id))
                logger.info(f"Subscribed to source {source_id} events")

                # Listen to events and emit events as they arrive
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            event_data = json.loads(message["data"])
                            event = SourceEvent(**event_data)
                            yield event

                            if event.status in (SourceStatus.COMPLETED, SourceStatus.FAILED):
                                break

                        except json.JSONDecodeError:
                            logger.error("Invalid JSON in message")
                        except ValueError as e:
                            logger.error(f"Invalid event data: {e}")

        except Exception as e:
            logger.exception(f"Failed to stream source {source_id} events: {e}")
            yield SourceEvent(
                source_id=source_id,
                status=SourceStatus.FAILED,
                error=str(e),
                metadata={},
            )

    async def _publish_source_event(
        self,
        source_id: UUID,
        status: SourceStatus,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Publish source event to Redis."""
        event = SourceEvent(source_id=source_id, status=status, error=error, metadata=metadata or {})

        await self.event_publisher.publish_event(
            channel=Channels.Sources.events(source_id),
            message=event,
        )
