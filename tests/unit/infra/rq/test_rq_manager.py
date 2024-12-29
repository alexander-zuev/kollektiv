from unittest.mock import MagicMock

import pytest
from redis.exceptions import ConnectionError, TimeoutError
from rq import Queue

from src.infra.rq.rq_manager import RQManager
from src.infra.settings import settings


class TestRQManagerUnit:
    """Unit tests for RQManager."""

    def test_initialization(self, mock_sync_redis):
        """Test RQManager initialization."""
        manager = RQManager(redis_manager=mock_sync_redis)
        assert isinstance(manager, RQManager)
        assert manager._queue is None

    def test_queue_property(self, mock_sync_redis):
        """Test queue property creates and reuses queue."""
        manager = RQManager(redis_manager=mock_sync_redis)

        # First access creates queue
        queue = manager.queue
        assert isinstance(queue, Queue)
        assert queue.name == settings.redis_queue_name
        assert queue.connection == mock_sync_redis.get_sync_client()

        # Second access reuses queue
        queue2 = manager.queue
        assert queue2 is queue

    def test_enqueue_job_success(self, mock_sync_redis):
        """Test successful job enqueue."""
        manager = RQManager(redis_manager=mock_sync_redis)
        mock_queue = MagicMock()
        manager._queue = mock_queue

        test_func = MagicMock()
        test_args = ("arg1", "arg2")
        test_kwargs = {"kwarg1": "value1"}

        manager.enqueue_job(test_func, *test_args, **test_kwargs)
        mock_queue.enqueue.assert_called_once_with(test_func, *test_args, **test_kwargs)

    def test_enqueue_job_connection_error(self, mock_sync_redis):
        """Test job enqueue with connection error."""
        manager = RQManager(redis_manager=mock_sync_redis)
        mock_queue = MagicMock()
        mock_queue.enqueue.side_effect = ConnectionError("Test error")
        manager._queue = mock_queue

        with pytest.raises(ConnectionError, match="Failed to enqueue job: Test error"):
            manager.enqueue_job(MagicMock())

    def test_enqueue_job_timeout_error(self, mock_sync_redis):
        """Test job enqueue with timeout error."""
        manager = RQManager(redis_manager=mock_sync_redis)
        mock_queue = MagicMock()
        mock_queue.enqueue.side_effect = TimeoutError("Test timeout")
        manager._queue = mock_queue

        with pytest.raises(TimeoutError, match="Failed to enqueue job: Test timeout"):
            manager.enqueue_job(MagicMock())
