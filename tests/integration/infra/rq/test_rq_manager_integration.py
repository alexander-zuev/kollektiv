from unittest.mock import MagicMock

import pytest
import tenacity
from redis.exceptions import ConnectionError, TimeoutError
from rq import Queue

from src.infra.external.redis_manager import RedisManager
from src.infra.rq.rq_manager import RQManager
from src.infra.settings import settings


@pytest.fixture
def mock_redis_manager():
    """Fixture to mock RedisManager."""
    mock_manager = MagicMock(spec=RedisManager)
    mock_manager.get_sync_client.return_value = MagicMock()
    return mock_manager


@pytest.fixture
def rq_manager(mock_redis_manager):
    """Fixture to create an RQManager with a mocked RedisManager."""
    return RQManager(redis_manager=mock_redis_manager)


def test_queue_initialization(rq_manager):
    """Test that the queue is initialized correctly."""
    queue = rq_manager.queue
    assert isinstance(queue, Queue)
    assert queue.name == settings.redis_queue_name
    assert queue.connection == rq_manager.redis_manager.get_sync_client()


def test_enqueue_job_success(rq_manager):
    """Test successful job enqueue."""
    mock_queue = MagicMock()
    rq_manager._queue = mock_queue

    test_func = MagicMock()
    test_args = ("arg1", "arg2")
    test_kwargs = {"kwarg1": "value1"}

    rq_manager.enqueue_job(test_func, *test_args, **test_kwargs)
    mock_queue.enqueue.assert_called_once_with(test_func, *test_args, **test_kwargs)


def test_enqueue_job_connection_error(rq_manager):
    """Test job enqueue with connection error."""
    mock_queue = MagicMock()
    mock_queue.enqueue.side_effect = ConnectionError("Test error")
    rq_manager._queue = mock_queue

    with pytest.raises(tenacity.RetryError):
        rq_manager.enqueue_job(MagicMock())


def test_enqueue_job_timeout_error(rq_manager):
    """Test job enqueue with timeout error."""
    mock_queue = MagicMock()
    mock_queue.enqueue.side_effect = TimeoutError("Test timeout")
    rq_manager._queue = mock_queue

    with pytest.raises(TimeoutError):
        rq_manager.enqueue_job(MagicMock())
