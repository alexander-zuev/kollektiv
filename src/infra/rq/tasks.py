from __future__ import annotations

import asyncio
from uuid import UUID

from src.infra.logger import get_logger
from src.infra.rq.worker_services import WorkerServices
from src.models.content_models import Chunk
from src.models.job_models import JobStatus

logger = get_logger()


def process_documents_job(internal_job_id: UUID, document_ids: list[UUID]) -> None:
    """Sync entry point for processing documents job."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_process_documents_job_async(internal_job_id, document_ids))
        logger.info(f"Successfully processed documents job {internal_job_id}")
    except Exception as e:
        logger.exception(f"Error processing documents job {internal_job_id}: {e}")
        raise
    finally:
        loop.close()


async def _process_documents_job_async(internal_job_id: UUID, document_ids: list[UUID]) -> None:
    """Process list of documents into chunks and adds them to vector DB."""
    logger.info(f"Processing documents job {internal_job_id}")

    worker_services = await WorkerServices.get_instance()

    try:
        # 1. Set job status to IN_PROGRESS
        await worker_services.job_manager.update_job(internal_job_id, {"status": JobStatus.IN_PROGRESS})

        # 2. Get documents from DB
        documents = await worker_services.data_service.get_documents(document_ids)

        # 3. Process documents into chunks
        # chunks, chunk_ids = await worker_services.chunker.process_documents(documents)
        chunks = [
            Chunk(
                document_id=document_ids[0],
                source_id=document_ids[0],
                text="Chunk content",
                token_count=100,
                source_url="https://example.com",
                page_title="Example Page",
                headers={"header1": "value1", "header2": "value2"},
            )
        ]
        chunks_ids = [chunk.chunk_id for chunk in chunks]
        logger.info("Placeholder for processing documents into chunks")

        # 4. Store chunks in Supabase
        await worker_services.data_service.save_chunks(chunks)

        # 5. Add chunks to vector DB
        # await worker_services.vector_db.add_data(chunks)
        logger.info("Placeholder for adding chunks to vector DB")

        # 6. Store chunks in supabase
        logger.info("Placeholder for storage")

        # 6. Update job status to complete
        await worker_services.job_manager.mark_job_completed(
            internal_job_id,
        )

        # 7. publish completed event
        await worker_services.event_publisher.publish_event(
            {
                "job_id": str(internal_job_id),
                "status": "completed",
            }
        )

    except Exception as e:
        logger.exception(f"Error processing documents job {internal_job_id}: {e}")
        await worker_services.job_manager.mark_job_failed(internal_job_id, str(e))
        await worker_services.event_publisher.publish_event(
            {
                "job_id": str(internal_job_id),
                "status": "failed",
                "error": str(e),
            }
        )
        raise
