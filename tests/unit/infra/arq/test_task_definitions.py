from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from arq.jobs import Job

from src.infra.arq.serializer import deserialize
from src.infra.arq.task_definitions import (
    KollektivTaskResult,
    KollektivTaskStatus,
    _create_job_reference,
    _gather_job_results,
    publish_event,
)
from src.infra.events.channels import Channels
from src.models.pubsub_models import ContentProcessingEvent, ContentProcessingStage


@pytest.fixture
def mock_context():
    """Create a mock context with required components."""
    return {"arq_redis": Mock(), "worker_services": Mock()}


@pytest.fixture
def mock_job():
    """Create a mock ARQ job."""
    job = Mock(spec=Job)
    job.job_id = str(uuid4())
    return job


@pytest.fixture
def success_result():
    """Create a successful task result."""
    return KollektivTaskResult(
        status=KollektivTaskStatus.SUCCESS, message="Operation completed successfully", data={"key": "value"}
    )


@pytest.fixture
def failure_result():
    """Create a failed task result."""
    return KollektivTaskResult(
        status=KollektivTaskStatus.FAILED, message="Operation failed", data={"error": "test error"}
    )


def test_create_job_reference_success(mock_context):
    """Test successful job reference creation."""
    job_id = str(uuid4())

    with patch("src.infra.arq.task_definitions.Job") as mock_job_class:
        _create_job_reference(mock_context, job_id)

        mock_job_class.assert_called_once_with(
            job_id=job_id,
            redis=mock_context["arq_redis"],
            _deserializer=deserialize,  # Use the actual deserializer
        )


def test_create_job_reference_invalid_id(mock_context):
    """Test job reference creation with invalid job ID."""
    with pytest.raises(ValueError, match="Invalid job ID"):  # Changed to match the actual error
        with patch("src.infra.arq.task_definitions.Job", side_effect=ValueError("Invalid job ID")):
            _create_job_reference(mock_context, "invalid-id")


@pytest.mark.asyncio
async def test_gather_job_results_all_success(mock_context):
    """Test gathering results when all jobs succeed."""
    job_ids = [str(uuid4()) for _ in range(3)]
    success_results = [
        KollektivTaskResult(status=KollektivTaskStatus.SUCCESS, message=f"Success {i}") for i in range(3)
    ]

    mock_jobs = []
    for job_id, result in zip(job_ids, success_results, strict=False):
        mock_job = Mock(spec=Job)
        mock_job.job_id = job_id
        mock_job.result = AsyncMock(return_value=result)
        mock_jobs.append(mock_job)

    with patch("src.infra.arq.task_definitions._create_job_reference", side_effect=mock_jobs):
        results = await _gather_job_results(mock_context, job_ids, "test_operation")

        assert len(results) == 3
        assert all(r.status == KollektivTaskStatus.SUCCESS for r in results)


@pytest.mark.asyncio
async def test_gather_job_results_with_failures(mock_context):
    """Test gathering results when some jobs fail."""
    job_ids = [str(uuid4()) for _ in range(3)]
    mixed_results = [
        KollektivTaskResult(status=KollektivTaskStatus.SUCCESS, message="Success"),
        KollektivTaskResult(status=KollektivTaskStatus.FAILED, message="Failed 1"),
        KollektivTaskResult(status=KollektivTaskStatus.FAILED, message="Failed 2"),
    ]

    mock_jobs = []
    for job_id, result in zip(job_ids, mixed_results, strict=False):
        mock_job = Mock(spec=Job)
        mock_job.job_id = job_id
        mock_job.result = AsyncMock(return_value=result)
        mock_jobs.append(mock_job)

    with patch("src.infra.arq.task_definitions._create_job_reference", side_effect=mock_jobs):
        with pytest.raises(Exception, match="test_operation failed: 2 out of 3 jobs failed"):
            await _gather_job_results(mock_context, job_ids, "test_operation")


@pytest.mark.asyncio
async def test_gather_job_results_execution_error(mock_context):
    """Test gathering results when job execution fails."""
    job_ids = [str(uuid4())]
    mock_job = Mock(spec=Job)
    mock_job.job_id = job_ids[0]
    mock_job.result = AsyncMock(side_effect=Exception("Execution failed"))

    with patch("src.infra.arq.task_definitions._create_job_reference", return_value=mock_job):
        with pytest.raises(Exception, match="test_operation failed: Execution failed"):
            await _gather_job_results(mock_context, job_ids, "test_operation")


@pytest.mark.asyncio
async def test_publish_event_success(mock_context):
    """Test successful event publishing."""
    source_id = uuid4()
    event = ContentProcessingEvent(
        source_id=source_id,
        event_type="content_processing",  # Fixed: Use correct event type
        stage=ContentProcessingStage.STARTED,  # Fixed: Add required stage field
    )

    mock_context["worker_services"].event_publisher.publish_event = AsyncMock()

    result = await publish_event(mock_context, event)

    mock_context["worker_services"].event_publisher.publish_event.assert_called_once_with(
        channel=Channels.Sources.processing_channel(), message=event
    )

    assert result.status == KollektivTaskStatus.SUCCESS
    assert "Event published successfully" in result.message


@pytest.mark.asyncio
async def test_publish_event_connection_error(mock_context):
    """Test event publishing with connection error."""
    source_id = uuid4()
    event = ContentProcessingEvent(
        source_id=source_id, event_type="content_processing", stage=ContentProcessingStage.STARTED
    )

    mock_context["worker_services"].event_publisher.publish_event = AsyncMock(
        side_effect=ConnectionError("Redis connection failed")
    )

    result = await publish_event(mock_context, event)

    assert result.status == KollektivTaskStatus.FAILED
    assert "connection error" in result.message


@pytest.mark.asyncio
async def test_publish_event_unexpected_error(mock_context):
    """Test event publishing with unexpected error."""
    source_id = uuid4()
    event = ContentProcessingEvent(
        source_id=source_id, event_type="content_processing", stage=ContentProcessingStage.STARTED
    )

    mock_context["worker_services"].event_publisher.publish_event = AsyncMock(side_effect=Exception("Unexpected error"))

    result = await publish_event(mock_context, event)

    assert result.status == KollektivTaskStatus.FAILED
    assert "unexpected error" in result.message
