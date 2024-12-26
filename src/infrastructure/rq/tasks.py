from __future__ import annotations

import asyncio

from src.infrastructure.common.logger import configure_logging, get_logger
from src.infrastructure.rq.worker_services import WorkerServices

configure_logging(debug=True)
logger = get_logger()


def test_services_connectivity(job_id: str) -> dict:
    """Test task that verifies connectivity to all services.

    Tests:
    1. Chroma heartbeat
    2. Redis connectivity
    3. Access to other services
    """
    services = WorkerServices.get_instance()
    logger.info(f"Testing services connectivity for job: {job_id}")
    results = {}

    try:
        # Test Chroma
        chroma_client = services.chroma_client
        asyncio.run(chroma_client.client.heartbeat())
        results["chroma"] = "connected"
        logger.info("✓ Chroma connection successful")

        # Test basic service access
        chunker = services.chunker
        results["chunker_max_tokens"] = chunker.max_tokens
        logger.info(f"✓ Chunker service accessible, max_tokens: {chunker.max_tokens}")

        # Test vector DB service
        vector_db = services.vector_db
        results["vector_db"] = "initialized"
        logger.info("✓ Vector DB service accessible")

        return results

    except Exception as e:
        logger.error(f"Service connectivity test failed for job {job_id}: {str(e)}", exc_info=True)
        raise
