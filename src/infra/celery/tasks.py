import asyncio
from typing import Any, Literal, TypeVar
from uuid import UUID

from celery import chord, group
from pydantic import BaseModel

from src.core._exceptions import DatabaseError
from src.infra.celery.worker import celery_app
from src.infra.events.channels import Channels
from src.infra.logger import get_logger
from src.infra.settings import get_settings
from src.models.content_models import Chunk, Document, ProcessingEvent

T = TypeVar("T", bound=BaseModel)
logger = get_logger()
settings = get_settings()

# TODO: Implement general, abstract pydantic based serializer. I should not be f*cking with serialization every call.
# TODO: Perhaps a feature request for celery?
# TODO: There has to be a more manageble way
# TODO: It should better handle partial processing failures.


def _publish_processing_event(
    source_id: UUID,
    event_type: Literal["processing", "completed", "failed"],
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Publish a processing event to the event bus."""
    services = celery_app.services

    event = ProcessingEvent(source_id=source_id, event_type=event_type, error=error, metadata=metadata)
    asyncio.run(services.event_publisher.publish_event(channel=Channels.CONTENT_PROCESSING, message=event))


@celery_app.task(
    acks_late=True,
    retry_backoff=True,
    max_retries=3,
)
def notify_processing_complete(results: list, user_id: str, source_id: str) -> None:
    """Task to be executed when all tasks in a group are complete."""
    logger.info(f"Publishing to pub/sub channel {Channels.CONTENT_PROCESSING}")

    # Check if any tasks failed
    failures = [r for r in results if r.get("status") == "failed"]

    if failures:
        _publish_processing_event(
            source_id=UUID(source_id),
            event_type="failed",
            error=f"Failed to process {len(failures)} chunks",
            metadata={"failures": failures},
        )
    else:
        _publish_processing_event(
            source_id=UUID(source_id), event_type="completed", metadata={"total_processed": len(results)}
        )


@celery_app.task(
    acks_late=True,
    retry_backoff=True,
    max_retries=3,
)
def generate_summary(results: list, source_id: str, documents: list[str]) -> None:
    """Generate a summary for a source."""
    logger.info(f"Chunking complete, generating summary for source {source_id}")
    documents = [Document.model_validate(doc) for doc in documents]
    try:
        asyncio.run(celery_app.services.summary_manager.prepare_summary(UUID(source_id), documents))

        event = ProcessingEvent(
            source_id=UUID(source_id),
            event_type="summary_generated",
            metadata={"total_documents": len(documents)},
        )
        asyncio.run(
            celery_app.services.event_publisher.publish_event(channel=Channels.CONTENT_PROCESSING, message=event)
        )
    except Exception as e:
        logger.exception(f"Error generating summary: {e}")
        raise e


@celery_app.task(
    acks_late=True,  # Only ack after successful completion
    retry_backoff=True,  # Exponential backoff between retries
    retry_kwargs={"max_retries": 3},
    track_started=True,  # Allows tracking task progress
)
def process_documents(documents: list[str], user_id: str, source_id: str) -> dict:
    """Entry point for processing list[Document].

    Args:
    - documents: serialized as JSON strings.
    - user_id: str of the user that is processing the documents
    - source_id: str of the source to be processed
    """
    # Get access to the services
    services = celery_app.services
    try:
        # Get back the docs
        docs = [Document.model_validate(doc) for doc in documents]
        logger.info(f"Processing {len(docs)} documents")

        # Break down into batches
        document_batches = services.chunker.batch_documents(docs)
        serialized_batches = [
            [doc.model_dump(mode="json") for doc in batch]  # Serialize each doc in each batch
            for batch in document_batches
        ]

        # Setup batch processing of the documents
        processing_tasks = group(process_document_batch.s(doc_batch, user_id) for doc_batch in serialized_batches)
        notification = notify_processing_complete.s(user_id, source_id)
        summary_task = generate_summary.s(source_id, documents)
        chord(processing_tasks)(summary_task | notification)

        return {"status": "started", "total_documents": len(docs)}
    except Exception as e:
        logger.exception(f"Error processing documents: {e}")
        _publish_processing_event(source_id=UUID(source_id), event_type="failed", error=str(e))
        return {"status": "failed", "message": str(e)}


@celery_app.task(
    acks_late=True,
    retry_backoff=True,
)
def process_document_batch(document_batch: list[Document], user_id: str) -> dict:
    """Process a batch of documents."""
    # Get access to the services
    try:
        services = celery_app.services
        documents = [Document.model_validate(doc) for doc in document_batch]
        chunks = services.chunker.process_documents(documents=documents)

        chunk_batches = services.chunker.batch_chunks(chunks)
        serialized_batches = [
            [chunk.model_dump(mode="json") for chunk in batch]  # Serialize each chunk in each batch
            for batch in chunk_batches
        ]

        task_group = group(add_chunk_to_storage.s(chunk_batch, user_id) for chunk_batch in serialized_batches)
        result = task_group.apply_async()
        logger.info(f"Processing job in celery enqueued with id {result.id}")
        return {"status": "success", "message": f"Successfully created {len(chunks)} chunks"}
    except Exception as e:
        logger.exception(f"Error processing document batch: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    acks_late=True,
    retry_backoff=True,
    max_retries=3,
)
def add_chunk_to_storage(chunk_batch: list[Chunk], user_id: str) -> dict:
    """Process a batch of chunks."""
    try:
        # 1. Get access to the services
        services = celery_app.services
        chunks = [Chunk.model_validate(chunk) for chunk in chunk_batch]

        # 2. Store and embed the chunks
        logger.info(f"Adding {len(chunks)} chunks to ChromaDB")
        asyncio.run(services.vector_db.add_data(chunks=chunks, user_id=UUID(user_id)))

        # 3. Persist the chunks to the database
        persist_to_db.delay([chunk.model_dump(mode="json") for chunk in chunks])

        return {"status": "success", "message": f"Successfully added {len(chunk_batch)} chunks to ChromaDB"}

    except Exception as e:
        logger.exception(f"Error processing chunk batch: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    acks_late=True,
    retry_backoff=True,
    max_retries=3,
)
def persist_to_db(chunks: list[Chunk]) -> dict:
    """Persist the chunks to the database."""
    try:
        # Get services container
        services = celery_app.services

        # Validate and persist chunks
        logger.info(f"Persisting {len(chunks)} chunks to the database")
        chunks = [Chunk.model_validate(chunk) for chunk in chunks]
        logger.debug(f"Headers type: {type(chunks[0].headers)}")
        asyncio.run(services.data_service.save_chunks(chunks))

        # Return success message
        return {"status": "success", "message": f"Successfully persisted {len(chunks)} chunks to the database"}
    except DatabaseError as e:
        logger.exception(f"Error persisting chunks to the database: {e}")
        return {"status": "error", "message": str(e)}
