# TODO: Properly handle errors
# TODO: Implement validation for non-empty content during crawling to prevent passing empty pages to the chunker.
# TODO: Implement retries or error handling for pages that fail to be crawled (e.g., network errors).
# TODO: Provide more informative progress updates to the user during crawling (e.g., percentage completion).
# TODO: Notify users only in case of critical errors or if no valid content is found after crawling.
import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import requests
from firecrawl import FirecrawlApp
from pydantic import HttpUrl
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.crawling.exceptions import EmptyContentError, FireCrawlAPIError, FireCrawlConnectionError, JobNotCompletedError
from src.crawling.file_manager import FileManager
from src.crawling.job_manager import JobManager
from src.crawling.models import (
    CrawlData,
    CrawlJob,
    CrawlJobStatus,
    CrawlRequest,
    CrawlResult,
    WebhookEvent,
    WebhookEventType,
)
from src.utils.config import (
    BACKOFF_FACTOR,
    ENVIRONMENT,
    FIRECRAWL_API_KEY,
    FIRECRAWL_API_URL,
    JOB_FILE_DIR,
    MAX_RETRIES,
    RAW_DATA_DIR,
    WEBHOOK_URL,
)
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


class FireCrawler:
    """
    A class for crawling and mapping URLs using the Firecrawl API.

    This class handles the interaction with the FireCrawl API, managing crawl jobs,
    and processing crawl results.

    Args:
        job_manager (JobManager): Manager for handling crawl job lifecycle.
        file_manager (FileManager): Manager for handling file operations.
        api_key (str, optional): FireCrawl API key. Defaults to FIRECRAWL_API_KEY.
        api_url (str, optional): FireCrawl API URL. Defaults to FIRECRAWL_API_URL.
        data_dir (str, optional): Directory for raw data. Defaults to RAW_DATA_DIR.
        jobs_dir (str, optional): Directory for job files. Defaults to JOB_FILE_DIR.

    Attributes:
        api_key (str): The FireCrawl API key.
        api_url (str): The FireCrawl API base URL.
        raw_data_dir (str): Directory for storing raw crawl data.
        jobs_dir (str): Directory for storing job information.
        job_manager (JobManager): Manager for job operations.
        file_manager (FileManager): Manager for file operations.
        firecrawl_app (FirecrawlApp): Instance of FireCrawl API client.
    """

    def __init__(
        self,
        job_manager: JobManager,
        file_manager: FileManager,
        api_key: str = FIRECRAWL_API_KEY,
        api_url: str = FIRECRAWL_API_URL,
        data_dir: str = RAW_DATA_DIR,
        jobs_dir: str = JOB_FILE_DIR,
    ) -> None:
        self.api_key: str = api_key
        self.api_url = api_url
        self.raw_data_dir: str = data_dir
        self.jobs_dir: str = jobs_dir
        self.job_manager = job_manager
        self.file_manager = file_manager
        self.firecrawl_app = self._initialize_app()

    @base_error_handler
    def _initialize_app(self):
        app = FirecrawlApp(api_key=self.api_key)
        logger.info("FireCrawler app initialized successfully.")
        return app

    @base_error_handler
    async def map_url(self, url: HttpUrl) -> str:
        """
        Map the given URL and return structured results.

        Args:
            url (HttpUrl): The URL to be mapped.

        Returns:
            dict[str, Any] | None: A dictionary containing the status, input URL, total number of links, and the list
            of links. Returns None if mapping fails.

        Raises:
            Any exceptions that the mapping function or save_results method might raise.
        """
        logger.info(f"Mapping URL: {url}")

        site_map = self.firecrawl_app.map_url(url)
        logger.info("Map results received. Attempting to parse the results.")

        # extract links and calculate total
        links = site_map
        total_links = len(links)

        logger.info(f"Total number of links received: {total_links}")

        result = {"status": "success", "input_url": url, "total_links": total_links, "links": links, "method": "map"}

        filename = await self.file_manager.save_result(result)
        return filename

    # TODO: refactor into decorator? or exception? Why does it belong here?
    @staticmethod
    def is_retryable_error(exception):
        """Return True if the exception is an HTTPError with a status code we want to retry."""
        if isinstance(exception, HTTPError):
            return exception.response.status_code in [429, 500, 502, 503, 504]
        return False

    def _build_params(self, request: CrawlRequest) -> dict[str, Any]:
        """Returns complied firecrawl params based on the raw CrawlRequest."""
        params = {
            "limit": request.page_limit,
            "maxDepth": request.max_depth if request.max_depth else 5,
            "includePaths": request.include_patterns if request.include_patterns else [],
            "excludePaths": request.exclude_patterns if request.exclude_patterns else [],
            "scrapeOptions": {
                "formats": ["markdown"],
                "excludeTags": ["img"],
            },
        }
        if not request.webhook_url:
            # Use default webhook URL if none provided
            params["webhook"] = WEBHOOK_URL

        return params

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        retry=retry_if_exception_type((HTTPError, FireCrawlConnectionError)),
        wait=wait_exponential(multiplier=1, min=30, max=300),
        before_sleep=lambda retry_state: logger.info(
            f"Retryable error occurred. Retrying in {retry_state.next_action.sleep} seconds..."
        ),
    )
    async def start_crawl(self, request: CrawlRequest) -> CrawlJob:
        """Start a new crawl job with webhook configuration."""
        try:
            params = self._build_params(request)

            # Ensure webhook URL is set
            if not params.get("webhook"):
                params["webhook"] = WEBHOOK_URL

            logger.debug(f"Starting crawl with params: {params}")

            # Start FireCrawl job
            response = self.firecrawl_app.async_crawl_url(str(request.url), params)
            logger.info(f"Received response from FireCrawl: {response}")

            # Create tracked job
            job = await self.job_manager.create_job(firecrawl_id=response["id"], start_url=request.url)

            return job

        except HTTPError as err:
            if err.response.status_code == 429:
                raise FireCrawlAPIError("Rate limit exceeded") from err
            elif err.response.status_code >= 500:
                raise FireCrawlConnectionError(f"FireCrawl API error: {err}") from err
            raise FireCrawlAPIError(f"FireCrawl API error: {err}") from err
        except RequestException as err:
            raise FireCrawlConnectionError(f"Connection error: {err}") from err

    @base_error_handler
    async def get_results(self, job_id: str) -> CrawlResult:
        """Get final results for a completed job."""
        job = await self.job_manager.get_job(job_id)
        if not job or job.status != CrawlJobStatus.COMPLETED:
            raise JobNotCompletedError(f"Job {job_id} not complete")

        # Get the crawl data
        crawl_data = await self._accumulate_crawl_results(job.firecrawl_id)

        # Extract unique URLs from metadata
        unique_links = set()
        for page in crawl_data.data:
            metadata = page.get("metadata", {})
            # Add og:url if present
            if og_url := metadata.get("og:url"):
                unique_links.add(og_url)

        # Create result with proper structure
        result = CrawlResult(
            job_status=job.status,
            input_url=str(job.start_url),
            total_pages=len(crawl_data.data),
            unique_links=list(unique_links),  # Convert set to list
            data=crawl_data,
            completed_at=datetime.now(timezone.utc),
            method=job.method,
        )

        return result

    @base_error_handler
    async def _accumulate_crawl_results(self, job_id: str) -> CrawlData:
        """
        Accumulate all crawling results for a given job ID.

        Args:
            job_id (str): The unique identifier of the crawling job.

        Returns:
            CrawlData:  CrawlData object containing the accumulated crawl results.
        """
        next_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
        crawl_data = []

        while next_url:
            logger.info("Accumulating job results.")
            batch_data, next_url = await self._fetch_results_from_url(next_url)
            crawl_data.extend(batch_data["data"])

        if not crawl_data:
            logger.error(f"No data accumulated for job {job_id}")
            raise EmptyContentError(f"No content found for job {job_id}")

        logger.info("No more pages to fetch. Returning results")

        return CrawlData(data=crawl_data)

    @base_error_handler
    async def _fetch_results_from_url(self, next_url: HttpUrl) -> tuple[dict[str, Any], str | None]:
        """
        Fetch the next batch of results from the given URL with retries.

        Args:
            next_url (HttpUrl): The URL to fetch the next batch of results from.

        Returns:
            tuple[dict[str, Any], str | None]: A tuple containing the batch data as a dictionary and the next URL as a
            string or None.

        Raises:
            RequestException: If an error occurs while making the HTTP request and the maximum number of retries is
            reached.
        """
        max_retries = MAX_RETRIES
        backoff_factor = BACKOFF_FACTOR

        for attempt in range(max_retries):
            try:
                logger.info(f"Trying to fetch the batch results for {next_url}")
                url = next_url
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"Received status code {response.status_code} from API.")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to fetch results after {max_retries} attempts.")
                        break
                    else:
                        wait_time = backoff_factor**attempt
                        logger.warning(
                            f"Request failed with status code {response.status_code}. "
                            f"Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                        continue

                batch_data = response.json()
                next_url = batch_data.get("next")  # if it's missing -> there are no more pages to crawl
                return batch_data, next_url
            except RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch results after {max_retries} attempts: {str(e)}")
                    raise
                else:
                    wait_time = backoff_factor**attempt
                    logger.warning(f"Request failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        # raise Exception("Failed to fetch results after maximum retries")
        logger.error("Failed to fetch results after maximum retries or received error responses.")
        return {"data": []}, None

    @base_error_handler
    async def crawl(self, request: CrawlRequest) -> CrawlJob:
        """
        Start a crawl job. Webhook URL is configured via environment.

        Args:
            request (CrawlRequest): The crawl request configuration

        Returns:
            CrawlJob: The created crawl job

        Raises:
            FireCrawlAPIError: For API-related errors
            FireCrawlConnectionError: For connection issues
        """
        logger.info(f"Starting crawl of {request.url} in {ENVIRONMENT} environment")
        logger.info(f"Using webhook URL: {WEBHOOK_URL}")

        try:
            job = await self.start_crawl(request)
            logger.info(f"Created job {job.id}")
            return job

        except (FireCrawlAPIError, FireCrawlConnectionError) as e:
            logger.error(f"Crawl failed: {str(e)}")
            raise


async def initialize_components():
    """Initialize required components"""
    job_manager = JobManager(JOB_FILE_DIR)
    file_manager = FileManager(RAW_DATA_DIR)

    crawler = FireCrawler(
        job_manager=job_manager,
        file_manager=file_manager,
        api_key=FIRECRAWL_API_KEY,
        data_dir=RAW_DATA_DIR,
        jobs_dir=JOB_FILE_DIR,
    )
    return crawler, job_manager


async def main():
    """Test crawler functionality locally"""
    logger.info("Starting local crawler test")

    try:
        # 1. Initialize components properly
        crawler, job_manager = await initialize_components()

        # 2. Create test crawl request
        request = CrawlRequest(
            url="https://docs.anthropic.com/en/docs/welcome",
            page_limit=5,  # Small limit for testing
            exclude_patterns=["/blog/*"],
        )

        # 3. Start crawl
        logger.info(f"Starting crawl of {request.url}")
        job = await crawler.crawl(request)
        logger.info(f"Created job {job.id}")

        # 4. Monitor job status
        while True:
            job = await job_manager.get_job(job.id)
            logger.info(f"Job status: {job.status}, Progress: {job.progress_percentage:.1f}%")

            if job.status == CrawlJobStatus.COMPLETED:
                logger.info("Job completed, fetching results...")
                try:
                    # Get results from crawler
                    result = await crawler.get_results(job.id)

                    # Save results using file manager
                    filename = await crawler.file_manager.save_result(result)

                    # Update job with result file
                    job.result_file = filename
                    await job_manager.update_job(job)

                    logger.info(f"Successfully saved results to {filename}")
                except Exception as e:
                    logger.error(f"Failed to fetch or save results: {str(e)}")
                break
            elif job.status == CrawlJobStatus.FAILED:
                logger.error(f"Job failed: {job.error}")
                break

            await asyncio.sleep(10)

        logger.info(f"Job finished with status: {job.status}")

    except FireCrawlAPIError as e:
        logger.error(f"API Error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


def run_crawler():
    """Entry point for the crawler script"""
    configure_logging(debug=True)
    asyncio.run(main())


if __name__ == "__main__":
    run_crawler()
