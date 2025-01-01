from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.core.content.chunker import MarkdownChunker
from src.infra.celery.worker import celery_app
from src.infra.logger import get_logger
from src.models.content_models import Chunk, Document

T = TypeVar("T", bound=BaseModel)
logger = get_logger()


@celery_app.task
def process_documents(document_ids: list[UUID], user_id: UUID) -> None:
    """Entry point for processing documents."""

    # Task to load documents

    # Separate into batches

    # Add processing of batches tasks

    # Aggregate

    # [PARALLEL]
    # Setup saving of saving of results


@celery_app.task
def aggregate_processing_results(results: list[UUID]) -> list[Chunk]:
    """Aggregate the processing results."""

    # Aggregate the results

    # Return the aggregated results


@celery_app.task
def process_batch(batch: list[Document], chunker: MarkdownChunker) -> list[Chunk]:
    """Process a batch of documents."""

    # Process the batch

    # Return the chunks


@celery_app.task
def persist_data_to_db(data: list[T]) -> None:
    """Save data to the database."""

    # Save the data


@celery_app.task
def load_data_from_db(ids: list[UUID]) -> list[T]:
    """Abstract loading of data from the database using data repository."""
    pass
