from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.api.v0.schemas.webhook_schemas import FireCrawlEventType, FireCrawlWebhookEvent, WebhookProvider
from src.models.content_models import (
    AddContentSourceRequest,
    ContentSourceConfig,
    DataSource,
    DataSourceType,
    FireCrawlSourceMetadata,
    SourceStatus,
)
from src.models.job_models import CrawlJobDetails, Job, JobStatus, JobType
from src.services.content_service import ContentService


@pytest.fixture
def mock_dependencies():
    """Basic dependencies needed for ContentService unit tests."""
    mock_crawler = AsyncMock()
    # Create a response object with proper attributes
    crawler_response = AsyncMock()
    crawler_response.success = True
    crawler_response.job_id = "test-crawl-id"
    mock_crawler.start_crawl.return_value = crawler_response

    mock_job_manager = AsyncMock()
    mock_job_manager.create_job.return_value = None

    mock_data_service = AsyncMock()
    mock_data_service.save_datasource.return_value = None
    mock_data_service.save_user_request.return_value = None
    mock_data_service.update_datasource.return_value = None

    mock_redis = AsyncMock()
    mock_event_publisher = AsyncMock()

    return {
        "crawler": mock_crawler,
        "job_manager": mock_job_manager,
        "data_service": mock_data_service,
        "redis_manager": mock_redis,
        "event_publisher": mock_event_publisher,
    }


@pytest.fixture
def content_service(mock_dependencies):
    """ContentService instance with mocked dependencies."""
    return ContentService(**mock_dependencies)


@pytest.fixture
def sample_source_request():
    """Sample source request for testing."""
    return AddContentSourceRequest(
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
        request_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_type=DataSourceType.WEB,
        request_config=ContentSourceConfig(
            url="https://example.com",
            page_limit=1,
            exclude_patterns=[],
            include_patterns=[],
        ),
    )


@pytest.fixture
def sample_data_source(sample_source_request):
    """Sample data source for testing."""
    return DataSource(
        source_id=UUID("00000000-0000-0000-0000-000000000002"),
        user_id=sample_source_request.user_id,
        request_id=sample_source_request.request_id,
        source_type=DataSourceType.WEB,
        status=SourceStatus.PENDING,
        metadata=FireCrawlSourceMetadata(
            crawl_config=sample_source_request.request_config,
            total_pages=0,
        ),
    )


class TestContentService:
    """Unit tests for ContentService."""

    async def test_add_source_success(
        self, content_service, mock_dependencies, sample_source_request, sample_data_source
    ):
        """Test successful source addition flow."""
        # Setup mocks
        mock_dependencies["data_service"].save_datasource.return_value = sample_data_source
        mock_dependencies["data_service"].save_user_request.return_value = sample_source_request
        mock_dependencies["data_service"].update_datasource.return_value = sample_data_source
        mock_dependencies["data_service"].update_datasource.return_value.status = SourceStatus.CRAWLING

        # Test
        response = await content_service.add_source(sample_source_request)

        # Verify
        assert response.status == SourceStatus.CRAWLING
        mock_dependencies["data_service"].save_datasource.assert_called_once()
        mock_dependencies["job_manager"].create_job.assert_called_once()

    async def test_handle_webhook_crawl_completed(self, content_service, mock_dependencies, sample_data_source):
        """Test successful webhook handling for crawl completion."""
        # Setup
        job = Job(
            job_id=UUID("00000000-0000-0000-0000-000000000001"),
            status=JobStatus.IN_PROGRESS,
            job_type=JobType.CRAWL,
            details=CrawlJobDetails(
                source_id=sample_data_source.source_id,
                firecrawl_id="test-crawl-id",
                pages_crawled=0,
                url="https://example.com",
            ),
        )
        mock_dependencies["job_manager"].get_by_firecrawl_id.return_value = job
        mock_dependencies["data_service"].get_datasource.return_value = sample_data_source

        # Test
        await content_service.handle_webhook_event(
            FireCrawlWebhookEvent(
                provider=WebhookProvider.FIRECRAWL,
                data={
                    "type": FireCrawlEventType.CRAWL_COMPLETED,
                    "id": "test-crawl-id",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "success": True,
                },
                raw_payload={},
            )
        )

        # Verify
        mock_dependencies["data_service"].update_datasource.assert_called_with(
            source_id=sample_data_source.source_id, updates={"status": SourceStatus.PROCESSING}
        )

    async def test_handle_webhook_crawl_failed(self, content_service, mock_dependencies, sample_data_source):
        """Test webhook handling for crawl failure."""
        # Setup
        error_message = "Network error during crawling"
        job = Job(
            job_id=UUID("00000000-0000-0000-0000-000000000001"),
            status=JobStatus.IN_PROGRESS,
            job_type=JobType.CRAWL,
            details=CrawlJobDetails(
                source_id=sample_data_source.source_id,
                firecrawl_id="test-crawl-id",
                pages_crawled=0,
                url="https://example.com",
            ),
        )
        mock_dependencies["job_manager"].get_by_firecrawl_id.return_value = job
        mock_dependencies["data_service"].get_datasource.return_value = sample_data_source

        # Test
        await content_service.handle_webhook_event(
            FireCrawlWebhookEvent(
                provider=WebhookProvider.FIRECRAWL,
                data={
                    "type": FireCrawlEventType.CRAWL_FAILED,
                    "id": "test-crawl-id",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "success": False,
                    "error": error_message,
                },
                raw_payload={},
            )
        )

        # Verify
        mock_dependencies["data_service"].update_datasource.assert_called_with(
            source_id=sample_data_source.source_id, updates={"status": SourceStatus.FAILED, "error": error_message}
        )
