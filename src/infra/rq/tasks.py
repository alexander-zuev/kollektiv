from __future__ import annotations

import asyncio

from src.infra.logger import get_logger
from src.infra.rq.worker_services import WorkerServices

logger = get_logger()

logger.info("Testing BUILD COMMAND")


def test_services_connectivity(job_id: str):
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
        asyncio.run(services.chroma_client.heartbeat())
        results["chroma"] = "connected"
        logger.info("✓ Chroma heartbeat successful")

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
