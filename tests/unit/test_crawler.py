from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import HTTPStatusError, TimeoutException
from tenacity import RetryError

from src.core._exceptions import CrawlerError
from src.core.content.crawler import FireCrawler
from src.infra.settings import get_settings
from src.models.firecrawl_models import CrawlParams, CrawlRequest

settings = get_settings()


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
@patch("src.core.content.crawler.FirecrawlApp.async_crawl_url")
async def test_start_crawl_retry_logic(mock_async_crawl_url):
    """Test that start_crawl retries on retryable errors but gives up after max attempts."""
    # Setup
    crawler = FireCrawler(api_key="test_key")
    request = CrawlRequest(url="http://example.com", page_limit=10)

    # Mock the API call to fail with a retryable error
    mock_async_crawl_url.side_effect = TimeoutException("Connection timed out")

    # Test that it eventually gives up after max retries
    with pytest.raises(RetryError):
        await crawler.start_crawl(request)

    # Verify the number of retry attempts matches settings
    expected_calls = settings.max_retries
    assert mock_async_crawl_url.call_count == expected_calls


# 4. Error Handling
@pytest.mark.asyncio
@pytest.mark.unit
@patch("src.core.content.crawler.FirecrawlApp.async_crawl_url")
async def test_start_crawl_non_retryable_error(mock_async_crawl_url):
    """Test that non-retryable HTTP errors raise CrawlerError immediately."""
    settings.max_retries = 1

    crawler = FireCrawler(api_key="test_key")
    request = CrawlRequest(url="http://example.com", page_limit=10, max_depth=2)

    # Mock a 400 error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    http_error = HTTPStatusError("HTTP Error", request=request, response=mock_response)
    http_error.response = mock_response
    mock_async_crawl_url.side_effect = http_error

    with pytest.raises(CrawlerError):
        await crawler.start_crawl(request)

    assert mock_async_crawl_url.call_count == 1  # Should fail immediately


# 5. Result Fetching
@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_results_from_url():
    """Test fetching and parsing results from FireCrawl API."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "markdown": "test content",
                "metadata": {
                    "title": "Test Title",
                    "description": "Test Description",
                    "sourceURL": "http://example.com",
                    "og:url": "http://example.com",
                },
            }
        ],
        "next": "http://api.firecrawl.dev/v1/crawl/next-page",
    }
    mock_response.raise_for_status = MagicMock()

    # Create async context manager mock
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        crawler = FireCrawler(api_key="test_key")
        test_url = "http://api.firecrawl.dev/v1/crawl/test-page"

        batch_data, next_url = await crawler._fetch_results_from_url(test_url)

        # Verify response parsing
        assert batch_data == mock_response.json.return_value
        assert next_url == "http://api.firecrawl.dev/v1/crawl/next-page"

        # Verify request parameters
        mock_client.get.assert_called_once_with(
            test_url, headers={"Authorization": f"Bearer {crawler.api_key}"}, timeout=30
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_results():
    """Test full get_results flow including pagination and document creation."""
    # Setup mock responses for pagination
    responses = [
        {
            "data": [
                {
                    "markdown": "page 1",
                    "metadata": {
                        "title": "Title 1",
                        "description": "Desc 1",
                        "sourceURL": "http://example.com/1",
                        "og:url": "http://example.com/1",
                    },
                }
            ],
            "next": "http://api.firecrawl.dev/v1/crawl/page2",
        },
        {
            "data": [
                {
                    "markdown": "page 2",
                    "metadata": {
                        "title": "Title 2",
                        "description": "Desc 2",
                        "sourceURL": "http://example.com/2",
                        "og:url": "http://example.com/2",
                    },
                }
            ],
            "next": None,
        },
    ]

    mock_responses = []
    for r in responses:
        mock_response = MagicMock()
        mock_response.json.return_value = r
        mock_response.raise_for_status = MagicMock()
        mock_responses.append(mock_response)

    mock_client = AsyncMock()
    mock_client.get.side_effect = mock_responses

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        crawler = FireCrawler(api_key="test_key")
        source_id = UUID("00000000-0000-0000-0000-000000000000")

        documents = await crawler.get_results("test_job_id", source_id)

        # Verify we got documents from both pages
        assert len(documents) == 2
        assert documents[0].content == "page 1"
        assert documents[1].content == "page 2"

        # Verify source_id was set correctly
        assert all(doc.source_id == source_id for doc in documents)

        # Verify metadata was created correctly
        assert documents[0].metadata.title == "Title 1"
        assert documents[1].metadata.title == "Title 2"
