import asyncio

from src.infrastructure.common.logger import configure_logging, get_logger


configure_logging(debug=True)
logger = get_logger()


def process_documents(job_id: str, documents: str) -> None:
    """Load documents into the vector database."""
    from src.infrastructure.rq.rq_worker import services

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
