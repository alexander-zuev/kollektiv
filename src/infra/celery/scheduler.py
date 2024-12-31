from uuid import uuid4

from src.infra.celery.tasks import process_documents
from src.infra.logger import configure_logging, get_logger

configure_logging()
logger = get_logger()


def schedule_chunking() -> None:
    """Schedule document processing task."""
    # Simulate some document IDs
    doc_ids = [uuid4() for _ in range(3)]
    user_id = uuid4()

    # Schedule the task
    result = process_documents.delay(doc_ids, user_id)

    # Wait for result (optional)
    chunks_created = result.get()
    logger.info(f"Task completed, created {chunks_created} chunks")


def schedule_tasks() -> None:
    """Schedule a set of tasks"""
    for n in range(100000):
        schedule_chunking()


if __name__ == "__main__":
    schedule_tasks()
