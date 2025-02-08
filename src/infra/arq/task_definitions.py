import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from src.infra.arq.worker_services import WorkerServices
from src.infra.events.channels import Channels
from src.infra.logger import get_logger
from src.infra.settings import get_settings
from src.models.content_models import Chunk, Document, ProcessingEvent

# Define types
T = TypeVar("T", bound=BaseModel)
logger = get_logger()
settings = get_settings()

# Define task function
TaskFunction = Callable[[dict[str, Any], ...], Awaitable[Any]]

# Example BaseModle

# Sample test data
SAMPLE_CHUNKS = [
    Chunk(
        chunk_id=uuid4(),
        text=f"Sample chunk content {i}",
        document_id=uuid4(),
        source_id=uuid4(),
        headers={"header1": "value1"},
        token_count=100,
        page_title=f"Page {i}",
        page_url=f"https://example.com/page{i}",
    )
    for i in range(1, 11)  # Creates 10 chunks
]

SAMPLE_DOCUMENTS = [
    Document(
        document_id=uuid4(),
        source_id=uuid4(),
        content="Sample document content with multiple chunks",
        metadata={"type": "test", "category": "sample"},
    ),
    Document(
        document_id=uuid4(),
        source_id=uuid4(),
        content="Another sample document with remaining chunks",
        metadata={"type": "test", "category": "sample"},
    ),
]


async def count_to_ten(ctx: dict[str, Any], n: int) -> None:
    """Count to ten."""
    logger.info(f"Counting to {n}")
    for i in range(n):
        logger.info(f"Counting: {i}")
        await asyncio.sleep(1)
    return {"status": "success", "count": n}


async def process_documents_task(ctx: dict[str, Any], document_ids: list[str]) -> dict[str, Any]:
    """Process documents by IDs."""
    logger.info(f"Processing documents: {document_ids}")

    return {"status": "success", "processed_docs": document_ids, "timestamp": time.time()}


async def publish_event(ctx: dict[str, Any], event: ProcessingEvent) -> None:
    """Publish a processing event to the event bus."""
    services: WorkerServices = ctx["worker_services"]

    # event = ProcessingEvent(source_id=source_id, event_type=event_type, error=error, metadata=metadata)
    await services.event_publisher.publish_event(channel=Channels.Sources.processing_channel(), message=event)
    logger.debug(f"Event published by arq worker for {event.source_id} with type: {event.event_type}")


# Export tasks
task_list: list[TaskFunction] = [
    # add tasks here
    process_documents_task,
    count_to_ten,
    # pydantic_test_task,
]
