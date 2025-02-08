import asyncio
from uuid import uuid4

from src.infra.arq.redis_pool import RedisPool
from src.infra.logger import configure_logging, get_logger

logger = get_logger()
configure_logging()


async def main() -> None:
    """Main function."""
    redis_pool = await RedisPool.create_redis_pool()
    logger.info("Initialized redis pool")

    count_job = await redis_pool.enqueue_job("count_to_ten", n=10)
    logger.info(f"Scheduled count to ten: {count_job}")

    result = await count_job.result()
    logger.info(f"Count result: {result}")

    # document task
    document_ids = [str(uuid4()) for _ in range(2)]
    document_job = await redis_pool.enqueue_job("process_documents_task", document_ids=document_ids)
    logger.info(f"Scheduled document task: {document_job}")

    result = await document_job.result()
    logger.info(f"Document result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
