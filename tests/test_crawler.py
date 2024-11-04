from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from firecrawl import FirecrawlApp

from src.core._exceptions import FireCrawlAPIError, JobNotCompletedError
from src.core.content.crawler.crawler import FireCrawler
from src.models.common.jobs import CrawlJob, CrawlJobStatus
from src.models.content.firecrawl_models import CrawlData, CrawlRequest, CrawlResult


@pytest.fixture
def mock_job_manager():
    """Create a mock job manager with async methods."""
    manager = AsyncMock()
    manager.get_job = AsyncMock()
    manager.create_job = AsyncMock()
    manager.update_job = AsyncMock()
    return manager


@pytest.fixture
def mock_file_manager():
    """Create a mock file manager with async methods."""
    manager = AsyncMock()
    manager.save_result = AsyncMock()
    manager.load_result = AsyncMock()
    return manager


@pytest.fixture
def mock_firecrawl_app():
    """Create a mock FirecrawlApp."""
    app = Mock(spec=FirecrawlApp)
    app.async_crawl_url = Mock()
    return app


@pytest.fixture
def crawler(mock_job_manager, mock_file_manager, mock_firecrawl_app):
    """Create a FireCrawler instance with mock dependencies."""
    with patch("src.core.content.crawler.crawler.FirecrawlApp", return_value=mock_firecrawl_app):
        crawler = FireCrawler(
            job_manager=mock_job_manager,
            file_manager=mock_file_manager,
        )
        return crawler


class TestFireCrawler:
    """Test suite for FireCrawler class."""

    @pytest.mark.asyncio
    async def test_crawl_successful_job_creation(self, crawler, mock_job_manager):
        """
        Test successful crawl job creation and initialization.

        This is a critical unit test as job creation is the entry point for crawling.
        """
        # Arrange
        request = CrawlRequest(url="https://test.com", page_limit=10, exclude_patterns=["/exclude/*"])
        mock_firecrawl_response = {"id": "test_firecrawl_id"}
        mock_job = CrawlJob(
            id="test_job_id",
            firecrawl_id="test_firecrawl_id",
            status=CrawlJobStatus.PENDING,
            start_url="https://test.com",
        )

        with patch.object(crawler.firecrawl_app, "async_crawl_url", return_value=mock_firecrawl_response):
            mock_job_manager.create_job.return_value = mock_job

            # Act
            result = await crawler.crawl(request)

            # Assert
            assert result.id == "test_job_id"
            assert result.status == CrawlJobStatus.PENDING
            mock_job_manager.create_job.assert_awaited_once_with(
                firecrawl_id="test_firecrawl_id", start_url="https://test.com/"
            )

    @pytest.mark.asyncio
    async def test_get_results_incomplete_job(self, crawler, mock_job_manager):
        """
        Test getting results for an incomplete job.

        This is important as it validates proper job state handling.
        """
        # Arrange
        job_id = "test_job_id"
        incomplete_job = CrawlJob(
            id=job_id, firecrawl_id="test_firecrawl_id", status=CrawlJobStatus.IN_PROGRESS, start_url="https://test.com"
        )
        mock_job_manager.get_job.return_value = incomplete_job

        # Act & Assert
        with pytest.raises(JobNotCompletedError):
            await crawler.get_results(job_id)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_crawl_flow(self, crawler, mock_job_manager, mock_file_manager):
        """
        Test the complete crawl flow from request to results.

        This integration test validates the entire crawl lifecycle.
        """
        # Arrange
        request = CrawlRequest(url="https://test.com", page_limit=10)
        mock_job = CrawlJob(
            id="test_job_id",
            firecrawl_id="test_firecrawl_id",
            status=CrawlJobStatus.COMPLETED,
            start_url="https://test.com",
            completed_at=datetime.now(UTC),
        )

        mock_crawl_data = {"data": [{"markdown": "# Test Content", "metadata": {"og:url": "https://test.com/page1"}}]}

        # Mock the API responses
        with (
            patch.object(crawler.firecrawl_app, "async_crawl_url", return_value={"id": "test_firecrawl_id"}),
            patch.object(crawler, "_fetch_results_from_url", return_value=(mock_crawl_data, None)),
        ):
            mock_job_manager.create_job.return_value = mock_job
            mock_job_manager.get_job.return_value = mock_job
            mock_file_manager.save_result.return_value = "test_result.json"

            # Act
            job = await crawler.crawl(request)
            result = await crawler.get_results(job.id)

            # Assert
            assert isinstance(result, CrawlResult)
            assert result.job_status == CrawlJobStatus.COMPLETED
            assert result.total_pages == 1
            assert "https://test.com/page1" in result.unique_links

    @pytest.mark.asyncio
    async def test_crawl_api_error_handling(self, crawler):
        """
        Test proper handling of FireCrawl API errors.

        Validates error handling and retry logic.
        """
        # Arrange
        request = CrawlRequest(url="https://test.com", page_limit=10)

        with patch.object(crawler.firecrawl_app, "async_crawl_url", side_effect=FireCrawlAPIError("API Error")):
            # Act & Assert
            with pytest.raises(FireCrawlAPIError) as exc_info:
                await crawler.crawl(request)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accumulate_crawl_results_pagination(self, crawler):
        """
        Test accumulation of paginated crawl results.

        Validates proper handling of multi-page result fetching.
        """
        # Arrange
        job_id = "test_job_id"
        page1_data = {
            "data": [{"markdown": "Page 1", "metadata": {"url": "https://test.com/page1"}}],
            "next": "page2_url",
        }
        page2_data = {"data": [{"markdown": "Page 2", "metadata": {"url": "https://test.com/page2"}}], "next": None}

        # Mock paginated responses
        with patch.object(crawler, "_fetch_results_from_url") as mock_fetch:
            mock_fetch.side_effect = [(page1_data, "page2_url"), (page2_data, None)]

            # Act
            result = await crawler._accumulate_crawl_results(job_id)

            # Assert
            assert isinstance(result, CrawlData)
            assert len(result.data) == 2
            assert result.data[0]["markdown"] == "Page 1"
            assert result.data[1]["markdown"] == "Page 2"
            assert result.data[0]["metadata"]["url"] == "https://test.com/page1"
            assert result.data[1]["metadata"]["url"] == "https://test.com/page2"
            assert mock_fetch.call_count == 2
