from src.infra.arq.arq_settings import get_arq_settings
from src.infra.arq.serializer import deserialize, serialize
from src.infra.arq.task_definitions import task_list
from src.infra.arq.worker import WorkerSettings

arq_settings = get_arq_settings()


def test_worker_settings_configuration():
    """Test WorkerSettings class has correct configuration."""
    settings = WorkerSettings()

    # Test task configuration
    assert settings.functions == task_list

    # Test startup/shutdown handlers
    assert callable(settings.on_startup)
    assert callable(settings.on_shutdown)

    # Test Redis configuration
    assert settings.redis_settings == arq_settings.redis_settings

    # Test job configuration
    assert settings.health_check_interval == arq_settings.health_check_interval
    assert settings.max_jobs == arq_settings.max_jobs
    assert settings.max_retries == arq_settings.job_retries

    # Test serialization configuration
    assert settings.job_serializer == serialize
    assert settings.job_deserializer == deserialize

    # Test result configuration
    assert settings.keep_result == 60  # 60 seconds
