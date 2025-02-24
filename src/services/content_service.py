import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from arq import ArqRedis
from pydantic import ValidationError

from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent, WebhookProvider
from src.core._exceptions import CrawlerError, EntityNotFoundError, JobNotFoundError, NonRetryableError
from src.core.content.crawler import FireCrawler
from src.infra.decorators import generic_error_handler
from src.infra.events.channels import Channels
from src.infra.events.event_publisher import EventPublisher
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.models.content_models import (
    AddContentSourceRequest,
    AddContentSourceRequestDB,
    AddContentSourceResponse,
    ContentProcessingEvent,
    DataSource,
    DataSourceStatusResponse,
    FireCrawlSourceMetadata,
    SourceEvent,
    SourceOverview,
    SourceStage,
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
        arq_redis_pool: ArqRedis,
    ):
        self.crawler = crawler
        self.job_manager = job_manager
        self.data_service = data_service
        self.redis_manager = redis_manager
        self.event_publisher = event_publisher
        self.arq_redis_pool = arq_redis_pool

    @generic_error_handler
    async def add_source(self, request: AddContentSourceRequest, user_id: UUID) -> AddContentSourceResponse:
        """POST /sources entrypoint.

        Args:
            request: Validated request containing source configuration
            user_id: UUID of the user creating the source

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
            await self._save_user_request(AddContentSourceRequestDB.from_api_to_db(request))
            source = await self._create_and_save_datasource(request=request, user_id=user_id)
            logger.debug("STEP 1. Crawl started")

            # Publish event
            await self.event_publisher.publish_event(
                channel=Channels.content_processing_channel(source.source_id),
                message=ContentProcessingEvent(
                    source_id=source.source_id,
                    stage=source.stage,
                ),
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

            return AddContentSourceResponse.from_source(source)
        except CrawlerError as e:
            # Crawler error -> returns a response
            logger.exception(f"Crawling of the source failed: {e}")
            raise NonRetryableError(f"Crawling of the source failed: {e}") from e
        except Exception as e:
            # Infrastructure error -> returns a response
            logger.exception(f"Failed to add source: {e}")
            if source:
                await self.data_service.update_datasource(
                    source_id=source.source_id,
                    updates={"status": SourceStage.FAILED, "error": str(e)},
                )
            if job:
                await self.job_manager.update_job(
                    job_id=job.job_id, updates={"status": JobStatus.FAILED, "error": str(e)}
                )

            # Publish failed event
            await self.event_publisher.publish_event(
                channel=Channels.content_processing_channel(source.source_id),
                message=self.event_publisher.create_event(
                    source_id=source.source_id,
                    stage=SourceStage.FAILED,
                ),
            )
            raise NonRetryableError("An internal server error occured, we are working on it.") from e

    async def _create_and_save_datasource(self, request: AddContentSourceRequest, user_id: UUID) -> DataSource:
        """Initiates saving of the datasource record into the database."""
        data_source = DataSource(
            user_id=user_id,
            source_type=request.source_type,
            stage=SourceStage.CREATED,
            metadata=FireCrawlSourceMetadata(
                crawl_config=request.request_config,
                total_pages=0,
            ),
            request_id=request.request_id,
        )

        await self.data_service.save_datasource(data_source=data_source)
        logger.info(f"Data source {data_source.source_id} created successfully")

        return data_source

    async def _save_user_request(self, request: AddContentSourceRequestDB) -> None:
        logger.debug(f"Saving user request {request.model_dump()}")
        await self.data_service.save_user_request(request=request)
        logger.info(f"User request {request.request_id} saved successfully")

    async def get_source_status(self, source_id: UUID) -> DataSourceStatusResponse | None:
        """GET /sources/{source_id} entrypoint
        Returns DataSourceStatusResponse if source exists, otherwise returns None
        """
        try:
            source = await self.data_service.retrieve_datasource(source_id=source_id)
            return DataSourceStatusResponse.from_source(source)
        except EntityNotFoundError:
            logger.warning(f"Source {source_id} not found")
            return None

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
                updates={
                    "status": SourceStage.CRAWLING_STARTED,
                    "job_id": job.job_id,
                    "updated_at": datetime.now(UTC),
                },
            )
            logger.debug(f"Updated source {job.details.source_id} status to CRAWLING")

            # Publish crawling started event
            await self.event_publisher.publish_event(
                channel=Channels.content_processing_channel(job.details.source_id),
                message=self.event_publisher.create_event(
                    source_id=job.details.source_id,
                    stage=SourceStage.CRAWLING_STARTED,
                ),
            )
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
        firecrawl_id = job.details.firecrawl_id
        if not isinstance(firecrawl_id, str) or not firecrawl_id:
            raise ValueError(f"Invalid firecrawl_id: {firecrawl_id}")

        documents, source = await asyncio.gather(
            self.crawler.get_results(
                firecrawl_id=firecrawl_id,  # Now type checker knows this is str
                source_id=job.details.source_id,
            ),
            self.data_service.get_datasource(job.details.source_id),
        )

        # 2. Enqueue processing job
        processing_job = await self.arq_redis_pool.enqueue_job(
            "process_documents",
            documents,
            user_id=source.user_id,
            source_id=source.source_id,
        )
        logger.info(f"Enqueued processing job with id: {processing_job.job_id}")

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
                        total_pages=len(documents),
                    ),
                    "status": SourceStage.PROCESSING_SCHEDULED,
                    "job_id": processing_job.job_id,  # How dirty. Overwriting of the job id.
                    "updated_at": datetime.now(UTC),
                },
            ),
            self.event_publisher.publish_event(
                channel=Channels.content_processing_channel(source.source_id),
                message=self.event_publisher.create_event(
                    source_id=source.source_id,
                    stage=SourceStage.PROCESSING_SCHEDULED,
                ),
            ),
        )

        logger.debug(f"Updated source {source.source_id} status to PROCESSING")

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
            updates={"status": SourceStage.FAILED, "error": error, "updated_at": datetime.now(UTC)},
        )
        logger.debug(f"Updated source {source_id} status to FAILED")

        await self.event_publisher.publish_event(
            channel=Channels.content_processing_channel(source_id),
            message=self.event_publisher.create_event(
                source_id=source_id,
                stage=SourceStage.FAILED,
                error=error,
            ),
        )

    async def stream_source_events(
        self,
        source_id: UUID,
    ) -> AsyncGenerator[SourceEvent, None]:
        """Stream SSE events for a source."""
        try:
            # Subscribe to ContentProcessingEvent channel
            redis_client = await self.redis_manager.get_async_client()
            async with redis_client.pubsub() as pubsub:
                await pubsub.subscribe(Channels.content_processing_channel(source_id))
                logger.info(
                    f"Subscribed to source {source_id} events on channel {Channels.content_processing_channel(source_id)}"
                )

                # Listen to events and emit events as they arrive
                async for message in pubsub.listen():
                    # This assumes events are ContentProcessingEvent which is correct
                    if message["type"] == "message":
                        try:
                            event_data = json.loads(message["data"])
                            event = SourceEvent.from_processing_event(ContentProcessingEvent(**event_data))
                            logger.debug(f"Emitting event: {event}")
                            yield event
                            # Update source status based on final events
                            if event.stage == SourceStage.COMPLETED:
                                await self.data_service.update_datasource(
                                    source_id=source_id,
                                    updates={
                                        "status": SourceStage.COMPLETED,
                                        "updated_at": datetime.now(UTC),
                                    },
                                )
                                logger.info(f"Updated source {source_id} status to COMPLETED")
                                break
                            elif event.stage == SourceStage.FAILED:
                                await self.data_service.update_datasource(
                                    source_id=source_id,
                                    updates={
                                        "status": SourceStage.FAILED,
                                        "error": event.error,
                                        "updated_at": datetime.now(UTC),
                                    },
                                )
                                logger.info(f"Updated source {source_id} status to FAILED")
                                break
                        except (json.JSONDecodeError, ValueError, ValidationError) as e:
                            logger.error(f"Invalid event data: {e}")
                            raise

        except Exception as e:
            logger.exception(f"Failed to stream source {source_id} events: {e}")
            raise

    async def get_sources(self, user_id: UUID) -> list[SourceOverview]:
        """Build a list of SourceOverview objects from a list of SourceSummary objects."""
        sources = await self.data_service.list_source_summaries(user_id=user_id)
        if len(sources) == 0:
            logger.debug(f"No sources found for user {user_id}")
            return []

        return [
            SourceOverview(source_id=source.source_id, is_active=True, summary=source.summary) for source in sources
        ]
