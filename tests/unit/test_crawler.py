from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests

from src.core._exceptions import (
    FireCrawlAPIError,
    FireCrawlConnectionError,
    FireCrawlTimeoutError,
    JobNotCompletedError,
)
from src.core.content.crawler.crawler import FireCrawler
from src.models.common.jobs import CrawlJob, CrawlJobStatus
from src.models.content.firecrawl_models import CrawlParams, CrawlRequest, ScrapeOptions


@pytest.fixture
async def mock_firecrawl_app():
    """Mocks the FirecrawlApp for unit tests."""
    with patch("src.core.content.crawler.crawler.FirecrawlApp") as MockFirecrawlApp:
        mock_app = AsyncMock()
        yield mock_app


@pytest.fixture
async def crawler(mock_firecrawl_app):
    """Provides a configured crawler instance with mocked dependencies."""
    job_manager = AsyncMock()
    file_manager = AsyncMock()
    return FireCrawler(job_manager=job_manager, file_manager=file_manager)


@pytest.fixture
def crawl_request():
    """Provides a sample CrawlRequest object."""
    return CrawlRequest(url="https://www.example.com")


@pytest.fixture
def mock_job_manager():
    """Create a mock job manager with async methods."""
    manager = AsyncMock()
    manager.get_job = AsyncMock()
    manager.create_job = AsyncMock()
    return manager


@pytest.fixture
def mock_file_manager():
    """Create a mock file manager with async methods."""
    manager = AsyncMock()
    manager.save_result = AsyncMock()
    return manager


class TestFireCrawler:
    """Test suite for FireCrawler class."""

    @pytest.mark.asyncio
    async def test__build_params(self, crawler: FireCrawler, crawl_request: CrawlRequest) -> None:
        """Test building Firecrawl parameters from a CrawlRequest."""
        expected_params = CrawlParams(
            url=str(crawl_request.url),
            limit=crawl_request.page_limit,
            max_depth=crawl_request.max_depth,
            include_paths=[],
            exclude_paths=[],
            webhook=None,
            scrape_options=ScrapeOptions(),
        )
        assert crawler._build_params(crawl_request) == expected_params

    @pytest.mark.asyncio
    async def test__build_params_with_webhook(
        self, crawler: FireCrawler, crawl_request: CrawlRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test building Firecrawl parameters with a custom webhook URL."""
        monkeypatch.setenv("WEBHOOK_HOST", "https://custom-webhook.com")
        expected_webhook = f"https://custom-webhook.com{Routes.System.Webhooks.BASE}{Routes.System.Webhooks.FIRECRAWL}"
        expected_params = CrawlParams(
            url=str(crawl_request.url),
            limit=crawl_request.page_limit,
            max_depth=crawl_request.max_depth,
            include_paths=[],
            exclude_paths=[],
            webhook=expected_webhook,
            scrape_options=ScrapeOptions(),
        )
        assert crawler._build_params(crawl_request) == expected_params

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_success(self, crawler: FireCrawler) -> None:
        """Test successful fetching of results from a URL."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "next": None}
        mock_response.raise_for_status.return_value = None
        with patch("src.core.content.crawler.crawler.requests.get", return_value=mock_response) as mock_get:
            data, next_url = await crawler._fetch_results_from_url("test_url")
            assert data == {"data": [], "next": None}
            assert next_url is None
            mock_get.assert_called_once_with(
                "test_url", headers={"Authorization": f"Bearer {crawler.api_key}"}, timeout=30
            )

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_connection_error(self, crawler: FireCrawler):
        """Test handling of connection errors when fetching results."""
        with patch(
            "src.core.content.crawler.crawler.requests.get",
            side_effect=requests.exceptions.RequestException("Connection Error"),
        ):
            with pytest.raises(FireCrawlConnectionError) as exc_info:
                await crawler._fetch_results_from_url("test_url")
            assert "Connection Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_timeout_error(self, crawler: FireCrawler):
        """Test handling of timeout errors when fetching results."""
        with patch(
            "src.core.content.crawler.crawler.requests.get", side_effect=requests.exceptions.Timeout("Timeout Error")
        ):
            with pytest.raises(FireCrawlTimeoutError) as exc_info:
                await crawler._fetch_results_from_url("test_url")
            assert "Timeout Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_crawl_success(
        self, crawler: FireCrawler, mock_firecrawl_app: Mock, mock_job_manager: AsyncMock, crawl_request: CrawlRequest
    ):
        """Test successful crawl initiation."""
        mock_firecrawl_response = {"id": "test_firecrawl_id"}

        mock_job = CrawlJob(
            id="test_job_id",
            firecrawl_id="test_firecrawl_id",
            status=CrawlJobStatus.PENDING,
            start_url=str(crawl_request.url),
        )

        mock_firecrawl_app.async_crawl_url.return_value = mock_firecrawl_response
        mock_job_manager.create_job.return_value = mock_job

        result = await crawler.start_crawl(crawl_request)

        assert result == mock_job
        mock_firecrawl_app.async_crawl_url.assert_called_once()
        mock_job_manager.create_job.assert_awaited_once_with(
            firecrawl_id="test_firecrawl_id", start_url=crawl_request.url
        )

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_pagination(self, crawler: FireCrawler) -> None:
        """Test handling of paginated responses."""
        page1_data = {"data": [{"url": "page1"}], "next": "next_page_url"}
        page2_data = {"data": [{"url": "page2"}], "next": None}

        with patch("src.core.content.crawler.crawler.requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: page1_data),
                Mock(status_code=200, json=lambda: page2_data),
            ]
            data, next_url = await crawler._fetch_results_from_url("test_url")

        assert data == {"data": [{"url": "page1"}, {"url": "page2"}], "next": None}
        assert next_url is None

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_api_error(self, crawler: FireCrawler) -> None:
        """Test handling of Firecrawl API errors (non-retryable)."""
        with patch("src.core.content.crawler.crawler.requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=400, json=lambda: {"error": "Bad Request"})  # Non-retryable
            with pytest.raises(FireCrawlAPIError):
                await crawler._fetch_results_from_url("test_url")

    @pytest.mark.asyncio
    async def test_start_crawl_api_error(self, crawler: FireCrawler, mock_firecrawl_app: Mock) -> None:
        """Test API error handling during crawl initiation (non-retryable)."""
        mock_firecrawl_app.async_crawl_url.side_effect = FireCrawlAPIError("API Error")
        request = CrawlRequest(url="https://www.example.com")
        with pytest.raises(FireCrawlAPIError):
            await crawler.start_crawl(request)

    @pytest.mark.asyncio
    async def test_get_results_incomplete_job(self, crawler: FireCrawler, mock_job_manager: AsyncMock) -> None:
        """Test handling of incomplete and failed jobs."""
        job_id = "test_job_id"

        # Test incomplete job
        incomplete_job = CrawlJob(
            id=job_id, firecrawl_id="firecrawl_id", status=CrawlJobStatus.PENDING, start_url="https://test.com"
        )
        mock_job_manager.get_job.return_value = incomplete_job
        with pytest.raises(JobNotCompletedError):
            await crawler.get_results(job_id)

        # Test failed job - should raise JobNotCompletedError
        failed_job = CrawlJob(
            id=job_id,
            firecrawl_id="firecrawl_id",
            status=CrawlJobStatus.FAILED,
            start_url="https://test.com",
            error="Crawl failed",
        )
        mock_job_manager.get_job.return_value = failed_job
        with pytest.raises(JobNotCompletedError):  # Expecting same exception as incomplete job
            await crawler.get_results(job_id)

    @pytest.mark.asyncio
    async def test_get_results_unique_links(self, crawler: FireCrawler, mock_job_manager: AsyncMock):
        """Test extraction of unique links from metadata."""
        job_id = "test_job_id"
        completed_job = CrawlJob(
            id=job_id, firecrawl_id="firecrawl_id", status=CrawlJobStatus.COMPLETED, start_url="https://test.com"
        )
        mock_job_manager.get_job.return_value = completed_job

        # Mock _accumulate_crawl_results to return data with metadata containing URLs
        mock_crawl_data = {
            "data": [
                {"metadata": {"url": "unique_link_1", "og:url": "unique_link_2"}},
                {"metadata": {"url": "unique_link_1"}},  # Duplicate URL
                {"metadata": {}},  # No metadata
            ]
        }

        with patch.object(crawler, "_accumulate_crawl_results", return_value=mock_crawl_data):
            result = await crawler.get_results(job_id)

        assert result.unique_links == [
            "unique_link_2",
            "unique_link_1",
        ]  # Order doesn't matter for sets, so sort for comparison

    @pytest.mark.asyncio
    async def test__build_params_webhook_handling(
        self, crawler: FireCrawler, crawl_request: CrawlRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test building Firecrawl parameters with and without a custom webhook URL."""
        # Test with custom webhook
        crawl_request.webhook_url = "https://custom-webhook.com/test"
        params_with_custom_webhook = crawler._build_params(crawl_request)
        assert params_with_custom_webhook.webhook == "https://custom-webhook.com/test"

        # Test with default webhook from environment variable
        crawl_request.webhook_url = None
        monkeypatch.setenv("WEBHOOK_HOST", "https://default-webhook.com")
        params_with_default_webhook = crawler._build_params(crawl_request)
        assert params_with_default_webhook.webhook == "https://default-webhook.com/system/webhooks/firecrawl"

    @pytest.mark.asyncio
    async def test__fetch_results_from_url_multi_page_success(self, crawler: FireCrawler) -> None:
        """Test successful fetching of results from a URL with multiple pages."""
        page1_data = {"data": [{"url": "page1"}], "next": "next_page_url"}
        page2_data = {"data": [{"url": "page2"}], "next": "another_next_page"}
        page3_data = {"data": [{"url": "page3"}], "next": None}

        mock_responses = [
            Mock(status_code=200, json=lambda: page1_data),
            Mock(status_code=200, json=lambda: page2_data),
            Mock(status_code=200, json=lambda: page3_data),
        ]

        with patch("src.core.content.crawler.crawler.requests.get") as mock_get:
            mock_get.side_effect = mock_responses

            data, next_url = await crawler._fetch_results_from_url("test_url")

            assert data == {"data": [{"url": "page1"}, {"url": "page2"}, {"url": "page3"}], "next": None}
            assert next_url is None
            assert mock_get.call_count == 3  # Ensure all pages were requested
