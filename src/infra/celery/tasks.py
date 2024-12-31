import asyncio
from uuid import UUID

from src.infra.celery.worker import celery_app, worker_services
from src.infra.logger import get_logger

logger = get_logger()


@celery_app.task
def process_documents(document_ids: list[UUID], user_id: UUID) -> None:
    """Process documents using chunker."""
    logger.info(f"Processing documents: {document_ids}")

    try:
        # Run the async chunking operation in a new event loop
        chunks = asyncio.run(worker_services.chunker.create_fake_chunks(n_chunks=100))

        # Here you could do more with the chunks:
        # - Save to DB
        # - Process further
        # - etc.

        logger.info(f"Created {len(chunks)} chunks")
        return len(chunks)

    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        raise
