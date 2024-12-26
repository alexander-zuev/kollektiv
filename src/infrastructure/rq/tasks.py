from __future__ import annotations

import asyncio

from src.infrastructure.common.logger import get_logger
from src.infrastructure.rq.rq_worker import services
from src.infrastructure.rq.worker_services import WorkerServices

logger = get_logger()


def process_documents(job_id: str, documents: str, services: WorkerServices = services) -> None:
    """Load documents into the vector database."""
    logger.info(f"Processing documents for job: {job_id}")
    chroma_client = services.chroma_client
    asyncio.run(chroma_client.client.heartbeat())
    chunker = services.chunker
    chunker_max_tokens = chunker.max_tokens
    logger.info(f"Chunker max tokens: {chunker_max_tokens}")
    logger.info(f"Processing documents for job: {job_id}")

    print("proces_documents")


# # 1. Chunk documents
# chunks = chunker.chunk_documents(documents=documents)

# # 2. Load & embed into vector database
# await vector_db.add_documents(chunks)

# # 3. Return the results
# return chunks
