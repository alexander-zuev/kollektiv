"""Integration tests for ARQ worker settings."""

import pytest
from arq.connections import RedisSettings

from src.infra.arq.arq_settings import get_arq_settings
from src.infra.arq.serializer import deserialize, serialize
from src.infra.arq.task_definitions import task_list
from src.infra.arq.worker import WorkerSettings


@pytest.fixture
def worker_settings():
    """Create a fresh worker settings instance."""
    return WorkerSettings()


def test_worker_task_configuration(worker_settings):
    """Test that worker has all required tasks configured."""
    assert worker_settings.functions == task_list

    # Verify that all tasks are callable
    for task in worker_settings.functions:
        assert callable(task)


def test_worker_redis_configuration(worker_settings):
    """Test worker Redis configuration integration."""
    arq_settings = get_arq_settings()

    assert isinstance(worker_settings.redis_settings, RedisSettings)
    assert worker_settings.redis_settings == arq_settings.redis_settings


def test_worker_job_configuration(worker_settings):
    """Test worker job processing configuration."""
    arq_settings = get_arq_settings()

    assert worker_settings.health_check_interval == arq_settings.health_check_interval
    assert worker_settings.max_jobs == arq_settings.max_jobs
    assert worker_settings.max_retries == arq_settings.job_retries


def test_worker_serialization_configuration(worker_settings):
    """Test worker serialization configuration."""
    assert worker_settings.job_serializer == serialize
    assert worker_settings.job_deserializer == deserialize


def test_worker_lifecycle_handlers(worker_settings):
    """Test that worker has lifecycle handlers configured."""
    assert callable(worker_settings.on_startup)
    assert callable(worker_settings.on_shutdown)
