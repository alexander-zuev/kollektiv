from unittest.mock import MagicMock

from rq import Queue

from src.infrastructure.config.settings import settings
from src.infrastructure.rq.rq_manager import RQManager


class TestRQManagerUnit:
    """Unit tests for RQManager."""

    def test_initialization(self):
        """Test that RQManager initializes correctly."""
        mock_redis_client = MagicMock()
        rq_manager = RQManager(redis_client=mock_redis_client)

        # Verify that the queue is created with the correct name and connection
        assert isinstance(rq_manager.queue, Queue)
        assert rq_manager.queue.name == settings.redis_queue_name
        assert rq_manager.queue.connection == mock_redis_client

    def test_get_queue(self):
        """Test that get_queue returns the correct queue."""
        mock_redis_client = MagicMock()
        rq_manager = RQManager(redis_client=mock_redis_client)
        queue = rq_manager.get_queue()
        assert isinstance(queue, Queue)
        assert queue.name == settings.redis_queue_name

    def test_enqueue(self):
        """Test that enqueue method enqueues a job correctly."""
        mock_redis_client = MagicMock()
        rq_manager = RQManager(redis_client=mock_redis_client)
        mock_queue = MagicMock()
        rq_manager.queue = mock_queue

        # Mock task function
        mock_task = MagicMock()

        # Enqueue a job
        rq_manager.enqueue(mock_task, "arg1", key="value")

        # Verify that the enqueue method of the queue is called with the correct arguments
        mock_queue.enqueue.assert_called_once_with(mock_task, "arg1", key="value")
