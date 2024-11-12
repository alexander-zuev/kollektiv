from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError
from tenacity import RetryError

from src.core._exceptions import EmptyContentError, FireCrawlAPIError, FireCrawlConnectionError
from src.core.content.crawler.crawler import FireCrawler
from src.infrastructure.config.settings import settings
from src.models.content.firecrawl_models import CrawlParams, CrawlRequest


# 1. Initialization Tests
@pytest.mark.unit
def test_firecrawler_initialization():
    # Test valid initialization
    crawler = FireCrawler(api_key="test_key")
    assert crawler.api_key == "test_key"

    # Test initialization without API key
    with pytest.raises(ValueError):
        FireCrawler(api_key=None)


# 2. Parameter Building
@pytest.mark.unit
def test_build_params():
    crawler = FireCrawler(api_key="test_key")
    request = CrawlRequest(url="http://example.com/", page_limit=10, max_depth=2)
    params = crawler._build_params(request)
    assert isinstance(params, CrawlParams)
    assert params.url == "http://example.com/"


# 3. Retry Logic
@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.crawler.FirecrawlApp.async_crawl_url")
async def test_start_crawl_retry_logic(mock_async_crawl_url):
    """Test that start_crawl retries on retryable errors but gives up after max attempts."""
    # Setup
    crawler = FireCrawler(api_key="test_key")
    request = CrawlRequest(url="http://example.com", page_limit=10)

    # Mock the API call to fail with a retryable error
    mock_async_crawl_url.side_effect = FireCrawlConnectionError("Connection failed")

    # Test that it eventually gives up after max retries
    with pytest.raises(RetryError):
        await crawler.start_crawl(request)

    # Verify the number of retry attempts matches settings
    expected_calls = settings.max_retries
    assert mock_async_crawl_url.call_count == expected_calls


# 4. Error Handling
@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.crawler.FirecrawlApp.async_crawl_url")
async def test_start_crawl_non_retryable_error(mock_async_crawl_url):
    """Test that non-retryable HTTP errors (400) raise FireCrawlAPIError immediately."""
    settings.max_retries = 1

    crawler = FireCrawler(api_key="test_key")
    request = CrawlRequest(url="http://example.com", page_limit=10, max_depth=2)

    mock_response = MagicMock()
    mock_response.status_code = 400
    http_error = HTTPError("HTTP Error")
    http_error.response = mock_response
    mock_async_crawl_url.side_effect = http_error

    with pytest.raises(FireCrawlAPIError):
        await crawler.start_crawl(request)

    assert mock_async_crawl_url.call_count == 1  # Should fail immediately


@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.crawler.FirecrawlApp.async_crawl_url")
async def test_start_crawl_retryable_error(mock_async_crawl_url):
    """Test that retryable HTTP errors (503) trigger retry mechanism."""
    # Mock the wait function to return immediately
    with patch("tenacity.wait_exponential", return_value=lambda *args, **kwargs: 0.1):
        # Set up the error response
        mock_response = MagicMock()
        mock_response.status_code = 503
        http_error = HTTPError("HTTP Error")
        http_error.response = mock_response
        mock_async_crawl_url.side_effect = http_error

        # Configure settings for test
        original_max_retries = settings.max_retries
        settings.max_retries = 1  # This means: 1 initial try + 1 retry = 2 total attempts

        try:
            crawler = FireCrawler(api_key="test_key")
            request = CrawlRequest(url="http://example.com", page_limit=10, max_depth=2)

            with pytest.raises(RetryError):
                await crawler.start_crawl(request)

            # Verify the number of attempts
            total_attempts = settings.max_retries + 1  # initial attempt + retries
            assert mock_async_crawl_url.call_count == total_attempts, (
                f"Expected {total_attempts} total attempts (1 initial + {settings.max_retries} retries), "
                f"but got {mock_async_crawl_url.call_count}"
            )

        finally:
            settings.max_retries = original_max_retries


@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.crawler.requests.get")
async def test_accumulate_crawl_results_error_handling(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_get.return_value = mock_response

    crawler = FireCrawler(api_key="test_key")
    with pytest.raises(EmptyContentError):
        await crawler._accumulate_crawl_results("job_id")


# 5. Result Fetching
@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.crawler.requests.get")
async def test_fetch_results_from_url(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [], "next": None}
    mock_get.return_value = mock_response

    crawler = FireCrawler(api_key="test_key")
    batch_data, next_url = await crawler._fetch_results_from_url("http://example.com")
    assert batch_data == {"data": [], "next": None}
    assert next_url is None
