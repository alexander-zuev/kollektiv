import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from arq.jobs import Job
from pydantic import BaseModel

from src.infra.arq.serializer import deserialize
from src.infra.arq.worker_services import WorkerServices
from src.infra.events.channels import Channels
from src.infra.events.event_publisher import EventPublisher
from src.infra.logger import get_logger
from src.infra.settings import get_settings
from src.models.content_models import Chunk, Document
from src.models.pubsub_models import ContentProcessingEvent, ContentProcessingStage
from src.models.task_models import KollektivTaskResult, KollektivTaskStatus

# Define types
T = TypeVar("T", bound=BaseModel)
logger = get_logger()
settings = get_settings()

# Define task function - updated to handle varying parameter counts
TaskFunction = Callable[..., Awaitable[KollektivTaskResult]]


# HELPER FUNCTIONS
async def _gather_job_results(
    ctx: dict[str, Any], job_ids: list[str], operation_name: str
) -> list[KollektivTaskResult]:
    """Gather results from multiple ARQ jobs.

    Args:
        ctx: Context dictionary containing worker services and Redis connection
        job_ids: List of job IDs to gather results from
        operation_name: Name of the operation for error reporting

    Returns:
        list[KollektivTaskResult]: List of results from all jobs

    Raises:
        Exception: If any job failed with an exception or returned a failure status
    """
    try:
        # Create Job objects from IDs
        jobs = [_create_job_reference(ctx, job_id) for job_id in job_ids]
        results = await asyncio.gather(*[job.result() for job in jobs])

        # Check if any job returned a failure status
        failures = [r for r in results if r.status == KollektivTaskStatus.FAILED]
        if failures:
            logger.error(
                f"{operation_name} failed: {len(failures)} out of {len(results)} jobs failed. "
                f"First failure: {failures[0].message}"
            )
            raise Exception(
                f"{operation_name} failed: {len(failures)} out of {len(results)} jobs failed. "
                f"First failure: {failures[0].message}"
            )
        else:
            logger.info(f"{operation_name} completed successfully with {len(results)} jobs")

        return results

    except Exception as e:
        # This catches both gather exceptions and our failure check exception
        raise Exception(f"{operation_name} failed: {str(e)}") from e


def _create_job_reference(ctx: dict[str, Any], job_id: str) -> Job:
    """Create a job reference.

    Args:
        ctx: Context dictionary containing worker services
        job_id: ID of the job to create a reference for

    Returns:
        Job: Job reference

    Raises:
        Exception: If any error occurs
    """
    try:
        return Job(job_id=job_id, redis=ctx["arq_redis"], _deserializer=deserialize)
    except Exception as e:
        logger.exception(f"Error creating job reference: {e}")
        raise


async def publish_event(ctx: dict[str, Any], event: ContentProcessingEvent) -> KollektivTaskResult:
    """Publish a processing event to the event bus.

    Args:
        ctx: Context dictionary containing worker services
        event: Event to publish

    Returns:
        KollektivTaskResult: Success/failure status of the publish operation
    """
    services: WorkerServices = ctx["worker_services"]

    try:
        await services.event_publisher.publish_event(channel=Channels.Sources.processing_channel(), message=event)
        logger.debug(f"Event published by arq worker for {event.source_id} with type: {event.event_type}")

        return KollektivTaskResult(status=KollektivTaskStatus.SUCCESS, message="Event published successfully")

    except (ConnectionError, TimeoutError) as e:
        # Handle connection/timeout issues with Redis
        logger.error(f"Redis connection error while publishing event: {str(e)}")
        return KollektivTaskResult(
            status=KollektivTaskStatus.FAILED, message=f"Failed to publish event - connection error: {str(e)}"
        )

    except Exception as e:
        # Handle any other unexpected errors
        logger.exception(f"Unexpected error publishing event: {str(e)}")
        return KollektivTaskResult(
            status=KollektivTaskStatus.FAILED, message=f"Failed to publish event - unexpected error: {str(e)}"
        )


async def process_documents(
    ctx: dict[str, Any], documents: list[Document], user_id: UUID, source_id: UUID
) -> KollektivTaskResult:
    """Entry point for processing list[Document].

    Args:
        ctx: Context dictionary containing worker services and Redis connection
        documents: List of documents to process
        user_id: UUID of the user processing the documents
        source_id: UUID of the source being processed

    Returns:
        KollektivTaskResult: Status and job IDs for tracking
    """
    # Get access to the services
    logger.info(f"Processing {len(documents)} documents")

    if not documents:
        return KollektivTaskResult(
            status=KollektivTaskStatus.FAILED,
            message="No documents provided for processing",
        )

    services = ctx["worker_services"]
    try:
        # Break down document list into batches
        document_batches = services.chunker.batch_documents(documents)
        batch_jobs_ids = []
        for batch in document_batches:
            job = await ctx["arq_redis"].enqueue_job("chunk_document_batch", batch, user_id)
            batch_jobs_ids.append(job.job_id)
        logger.debug(f"Scheduled the following batch jobs: {batch_jobs_ids}")

        # 2. Schedule summary generation
        summary_job = await ctx["arq_redis"].enqueue_job("generate_summary", documents, source_id)
        summary_job_id = summary_job.job_id

        # 3. Schedule result checker
        checker_job = await ctx["arq_redis"].enqueue_job(
            "check_content_processing_complete", batch_jobs_ids, summary_job_id, user_id, source_id
        )

        # 4. Create success result
        result = KollektivTaskResult(
            status=KollektivTaskStatus.SUCCESS,
            message="Documents scheduled for processing",
            data={"batch_jobs": batch_jobs_ids, "checker_job_id": checker_job.job_id, "summary_job_id": summary_job_id},
        )

        # 5. Publish processing scheduled event
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.STARTED,
                source_id=source_id,
                metadata=result.data,
            ),
        )

        return result
    except Exception as e:
        logger.exception(f"Error processing documents: {e}")

        # Create failure result
        result = KollektivTaskResult(
            status=KollektivTaskStatus.FAILED,
            message=f"Setting up processing of documents failed: {str(e)}",
            data={"error": str(e)},
        )

        # Publish failure event
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.FAILED,
                source_id=source_id,
                error=result.message,
                metadata=result.data,
            ),
        )

        return result


async def chunk_document_batch(
    ctx: dict[str, Any], document_batch: list[Document], user_id: UUID
) -> KollektivTaskResult:
    """Process a batch of documents."""
    # Get access to the services
    try:
        services = ctx["worker_services"]
        # 1. Break down into chunks
        blocking = functools.partial(services.chunker.process_documents, documents=document_batch)
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(None, blocking)

        # 2. Break down into chunk batches
        blocking = functools.partial(services.chunker.batch_chunks, chunks=chunks)
        loop = asyncio.get_running_loop()
        chunk_batches = await loop.run_in_executor(None, blocking)

        # 3. Send chunks to storage
        chunk_job_ids = []
        for chunk_batch in chunk_batches:
            job = await ctx["arq_redis"].enqueue_job("persist_chunks", chunk_batch, user_id)
            chunk_job_ids.append(job.job_id)

        # Wait for all storage jobs to complete
        results = await _gather_job_results(ctx, chunk_job_ids, "chunk_document_batch")

        # Check results
        failures = [r for r in results if r.status == KollektivTaskStatus.FAILED]
        if failures:
            return KollektivTaskResult(
                status=KollektivTaskStatus.FAILED,
                message=f"Failed to store {len(failures)} chunk batches",
                data={"failures": failures},
            )

        return KollektivTaskResult(
            status=KollektivTaskStatus.SUCCESS,
            message=f"Successfully stored {len(chunk_job_ids)} chunk batches",
            data={"stored_chunks": len(chunk_job_ids)},
        )
    except Exception as e:
        logger.exception(f"Error processing document batch: {e}")
        return KollektivTaskResult(
            status=KollektivTaskStatus.FAILED,
            message=f"Failed to process document batch: {str(e)}",
        )


async def persist_chunks(ctx: dict[str, Any], chunk_batch: list[Chunk], user_id: UUID) -> KollektivTaskResult:
    """Adds chunks to supabase and Chroma."""
    try:
        services = ctx["worker_services"]

        await asyncio.gather(
            services.vector_db.add_data(chunks=chunk_batch, user_id=user_id),
            services.data_service.save_chunks(chunks=chunk_batch),
        )

        return KollektivTaskResult(
            status=KollektivTaskStatus.SUCCESS,
            message=f"Successfully added {len(chunk_batch)} chunks to storage",
            data={"stored_chunks": len(chunk_batch)},
        )
    except Exception as e:
        logger.exception(f"Error adding chunks to storage: {e}")
        return KollektivTaskResult(
            status=KollektivTaskStatus.FAILED, message=f"Failed to add chunks to storage: {str(e)}"
        )


async def generate_summary(ctx: dict[str, Any], documents: list[Document], source_id: UUID) -> KollektivTaskResult:
    """Generate a summary for a source."""
    logger.info(f"Chunking complete, generating summary for source {source_id}")
    try:
        services = ctx["worker_services"]
        await services.summary_manager.prepare_summary(source_id, documents)
        result = KollektivTaskResult(
            status=KollektivTaskStatus.SUCCESS,
            message=f"Successfully generated summary for source id {source_id}",
        )
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.SUMMARY_GENERATED,
                source_id=source_id,
                metadata={"total_documents": len(documents)},
            ),
        )
        return result
    except Exception as e:
        logger.exception(f"Error generating summary: {e}")
        return KollektivTaskResult(status=KollektivTaskStatus.FAILED, message=f"Failed to generate summary: {str(e)}")


async def check_content_processing_complete(
    ctx: dict[str, Any], chunk_batch_job_ids: list[str], summary_job_id: str, user_id: UUID, source_id: UUID
) -> KollektivTaskResult:
    """Check completion status of content processing jobs and publish appropriate event.

    Args:
        ctx: Context dictionary containing worker services and Redis connection
        chunk_batch_job_ids: List of job IDs to check completion for
        summary_job_id: ID of the summary generation job
        user_id: UUID of the user processing the documents
        source_id: UUID of the source being processed

    Returns:
        KollektivTaskResult: Status of the completion check
    """
    try:
        # 1. Check chunk processing results
        chunk_results = await _gather_job_results(ctx, chunk_batch_job_ids, "chunk_document_batch")
        chunk_failures = [r for r in chunk_results if r.status == KollektivTaskStatus.FAILED]

        if chunk_failures:
            result = KollektivTaskResult(
                status=KollektivTaskStatus.FAILED,
                message=f"Chunk processing failed: {len(chunk_failures)} chunks failed",
                data={"failures": chunk_failures},
            )
            await publish_event(
                ctx,
                EventPublisher._create_event(
                    stage=ContentProcessingStage.FAILED,
                    source_id=source_id,
                    error=result.message,
                    metadata={"failures": chunk_failures},
                ),
            )
            return result

        # 2. Publish chunks generated event
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.CHUNKS_GENERATED,
                source_id=source_id,
            ),
        )

        # 3. Check summary generation
        summary_job_results = await _gather_job_results(ctx, [summary_job_id], "summary_generation")
        summary_result = summary_job_results[0]
        if summary_result.status == KollektivTaskStatus.FAILED:
            result = KollektivTaskResult(
                status=KollektivTaskStatus.FAILED,
                message=f"Summary generation failed: {summary_result.message}",
            )
            await publish_event(
                ctx,
                EventPublisher._create_event(
                    stage=ContentProcessingStage.FAILED,
                    source_id=source_id,
                    error=result.message,
                ),
            )
            return result

        # 4. Publish final completion event
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.COMPLETED,
                source_id=source_id,
            ),
        )
        return KollektivTaskResult(
            status=KollektivTaskStatus.SUCCESS, message="Content processing completion check completed successfully."
        )

    except Exception as e:
        logger.exception(f"Error checking content processing completion: {e}")
        result = KollektivTaskResult(
            status=KollektivTaskStatus.FAILED,
            message=f"Failed to process chunking results and summary generation: {str(e)}",
        )
        await publish_event(
            ctx,
            EventPublisher._create_event(
                stage=ContentProcessingStage.FAILED,
                source_id=source_id,
                error=result.message,
                metadata={"error_type": "completion_check_failed"},
            ),
        )
        return result


# Export tasks
task_list: list[TaskFunction] = [
    publish_event,
    check_content_processing_complete,
    generate_summary,
    chunk_document_batch,
    process_documents,
    persist_chunks,
]
