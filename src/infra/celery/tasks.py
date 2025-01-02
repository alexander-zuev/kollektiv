import asyncio
from typing import TypeVar
from uuid import UUID

from celery import group
from pydantic import BaseModel

from src.infra.celery.worker import celery_app
from src.infra.logger import get_logger
from src.models.content_models import Chunk, Document

T = TypeVar("T", bound=BaseModel)
logger = get_logger()


@celery_app.task(
    acks_late=True,  # Only ack after successful completion
    retry_backoff=True,  # Exponential backoff between retries
    retry_kwargs={"max_retries": 3},
    track_started=True,  # Allows tracking task progress
)
def process_documents(documents: list[str], user_id: str) -> dict:
    """Entry point for processing list[Document].

    Args:
    - list[Document]: serialized as JSON strings.
    - user_id: str
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
        tasks = group(process_document_batch.s(doc_batch, user_id) for doc_batch in serialized_batches)
        result = tasks.apply_async()
        logger.info(f"Processing job in celery {result.id} enqueued")

        return {
            "status": "success",
            "total_documents": len(docs),
            "task_group_id": result.id,
        }
    except Exception as e:
        logger.exception(f"Error processing documents: {e}")
        return {"status": "error", "message": str(e)}


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
        logger.info(f"Processing job in celery {result.id} enqueued")
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
        services = celery_app.services
        logger.info(f"Persisting {len(chunks)} chunks to the database")
        chunks = [Chunk.model_validate(chunk) for chunk in chunks]
        asyncio.run(services.data_service.save_chunks(chunks))
        return {"status": "success", "message": f"Successfully persisted {len(chunks)} chunks to the database"}
    except Exception as e:
        logger.exception(f"Error persisting chunks to the database: {e}")
        return {"status": "error", "message": str(e)}
