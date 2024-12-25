from uuid import UUID

from src.core.content.chunker import MarkdownChunker
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.logger import get_logger
from src.models.content_models import Chunk

logger = get_logger()


def processing_task(
    source_id: UUID,
    job_id: UUID,
    chunker: MarkdownChunker,
    vector_db: VectorDB,
) -> list[Chunk]:
    """Processes documents and loads chunks to vector server."""
    try:
        # Process pages into chunks
        chunks = await chunker.process_pages(documents=documents)
        logger.info(f"Processed {len(chunks)} chunks for job {job_id}")

        # Load chunks to vector server
        await vector_db.add_documents(chunks)
        logger.info(f"Loaded {len(chunks)} chunks to vector server for job {job_id}")

        # Update job status
        await job_manager.update_job(job_id, updates={})

    except Exception as e:
        await job_manager.update_job(job_id, updates={})
        logger.error(f"Processing job {job_id} failed with error: {e}")
        raise
