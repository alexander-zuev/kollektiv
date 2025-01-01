from typing import TypeVar

from celery import group
from pydantic import BaseModel

from src.infra.celery.worker import celery_app
from src.infra.logger import get_logger
from src.models.content_models import Chunk, Document

T = TypeVar("T", bound=BaseModel)
logger = get_logger()


@celery_app.task
def process_documents(documents: list[Document]) -> None:
    """Entry point for processing documents."""
    # Get access to the services
    services = celery_app.services

    # Get back the docs
    docs = [model_validate(doc) for doc in documents]
    logger.info(f"Processing {len(docs)} documents")

    # Break down into batches
    document_batches = services.chunker.batch_documents(docs)

    # Setup batch processing of the documents
    tasks = group(process_document_batch.s(doc_batch) for doc_batch in document_batches)
    result = tasks.apply_async()
    logger.info(f"Processing job in celery {result.task_id} enqueued")


@celery_app.task
def process_document_batch(document_batch: list[Document]) -> None:
    """Process a batch of documents."""
    # Get access to the services
    services = celery_app.services
    chunks = services.chunker.chunk_documents(document_batch)

    chunk_batches = services.chunker.batch_chunks(chunks)

    task_group = group(process_chunk_batch.s(chunk_batch) for chunk_batch in chunk_batches)
    result = task_group.apply_async()
    logger.info(f"Processing job in celery {result.task_id} enqueued")


@celery_app.task
def process_chunk_batch(chunk_batch: list[Chunk]) -> None:
    """Process a batch of chunks."""
    # Get access to the services
    services = celery_app.services

    # 1. Store and embed the chunks
    services.vector_service.embed_chunks(chunk_batch)

    # 2. Persist the chunks to the database
    persist_to_db.delay(chunk_batch)


@celery_app.task
def persist_to_db(chunks: list[Chunk]) -> None:
    """Persist the chunks to the database."""
    services = celery_app.services
    services.data_service.save_chunks(chunks)
