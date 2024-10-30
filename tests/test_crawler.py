from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.crawling.crawler import (
    CrawlJob,
    CrawlJobStatus,
    CrawlRequest,
    CrawlResult,
    EmptyContentError,
    FireCrawler,
    JobNotCompletedError,
)
from src.crawling.file_manager import FileManager
from src.crawling.job_manager import JobManager
from src.utils.config import FIRECRAWL_API_KEY, WEBHOOK_URL

# Test data
TEST_URL = "https://docs.anthropic.com/claude/docs"
TEST_JOB_ID = "test-job-123"
TEST_FIRECRAWL_ID = "fc-123"


@pytest.fixture
def mock_job_manager():
    manager = AsyncMock(spec=JobManager)
    manager.create_job.return_value = CrawlJob(
        id=TEST_JOB_ID, firecrawl_id=TEST_FIRECRAWL_ID, status=CrawlJobStatus.PENDING, start_url=TEST_URL
    )
    return manager


@pytest.fixture
def mock_file_manager():
    return AsyncMock(spec=FileManager)


@pytest.fixture
def mock_firecrawl_app():
    app = Mock()
    app.async_crawl_url.return_value = {"id": TEST_FIRECRAWL_ID}
    app.map_url.return_value = ["url1", "url2"]
    return app


@pytest.fixture
def crawler(mock_job_manager, mock_file_manager):
    with patch("src.crawling.crawler.FirecrawlApp") as mock_app_class:
        mock_app_class.return_value = mock_firecrawl_app
        crawler = FireCrawler(job_manager=mock_job_manager, file_manager=mock_file_manager, api_key=FIRECRAWL_API_KEY)
        return crawler


class TestFireCrawler:
    """Test suite for FireCrawler class."""

    def test_initialization(self, crawler):
        """Test crawler initialization."""
        assert crawler.api_key == FIRECRAWL_API_KEY
        assert crawler.job_manager is not None
        assert crawler.file_manager is not None
        assert crawler.firecrawl_app is not None

    @pytest.mark.asyncio
    async def test_crawl_success(self, crawler, mock_job_manager):
        """Test successful crawl operation."""
        request = CrawlRequest(url=TEST_URL, page_limit=50, exclude_patterns=["/blog/*"])

        job = await crawler.crawl(request)

        assert job.id == TEST_JOB_ID
        assert job.status == CrawlJobStatus.PENDING
        assert job.start_url == TEST_URL
        mock_job_manager.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_results_completed_job(self, crawler, mock_job_manager):
        """Test getting results for a completed job."""
        # Setup completed job
        completed_job = CrawlJob(
            id=TEST_JOB_ID, firecrawl_id=TEST_FIRECRAWL_ID, status=CrawlJobStatus.COMPLETED, start_url=TEST_URL
        )
        mock_job_manager.get_job.return_value = completed_job

        # Mock crawl data
        mock_crawl_data = {"data": [{"content": "test", "metadata": {"og:url": TEST_URL}}]}

        with patch.object(crawler, "_fetch_results_from_url", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (mock_crawl_data, None)

            result = await crawler.get_results(TEST_JOB_ID)

            assert isinstance(result, CrawlResult)
            assert result.job_status == CrawlJobStatus.COMPLETED
            assert result.input_url == TEST_URL
            assert len(result.unique_links) == 1

    @pytest.mark.asyncio
    async def test_get_results_incomplete_job(self, crawler, mock_job_manager):
        """Test getting results for an incomplete job."""
        pending_job = CrawlJob(
            id=TEST_JOB_ID, firecrawl_id=TEST_FIRECRAWL_ID, status=CrawlJobStatus.PENDING, start_url=TEST_URL
        )
        mock_job_manager.get_job.return_value = pending_job

        with pytest.raises(JobNotCompletedError):
            await crawler.get_results(TEST_JOB_ID)

    @pytest.mark.asyncio
    async def test_accumulate_empty_results(self, crawler):
        """Test handling of empty crawl results."""
        with patch.object(crawler, "_fetch_results_from_url", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ({"data": []}, None)

            with pytest.raises(EmptyContentError):
                await crawler._accumulate_crawl_results(TEST_JOB_ID)

    @pytest.mark.asyncio
    async def test_map_url(self, crawler, mock_file_manager):
        """Test URL mapping functionality."""
        mock_file_manager.save_result.return_value = "test_file.json"

        filename = await crawler.map_url(TEST_URL)

        assert filename == "test_file.json"
        mock_file_manager.save_result.assert_called_once()

    def test_build_params(self, crawler):
        """Test crawl parameters building."""
        request = CrawlRequest(
            url=TEST_URL, page_limit=50, exclude_patterns=["/blog/*"], include_patterns=["/docs/*"], max_depth=3
        )

        params = crawler._build_params(request)

        assert params["limit"] == 50
        assert params["maxDepth"] == 3
        assert params["excludePaths"] == ["/blog/*"]
        assert params["includePaths"] == ["/docs/*"]
        assert params["webhook"] == WEBHOOK_URL
        assert params["scrapeOptions"]["formats"] == ["markdown"]
