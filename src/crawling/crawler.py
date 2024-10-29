# TODO: Properly handle errors
# TODO: Implement validation for non-empty content during crawling to prevent passing empty pages to the chunker.
# TODO: Implement retries or error handling for pages that fail to be crawled (e.g., network errors).
# TODO: Provide more informative progress updates to the user during crawling (e.g., percentage completion).
# TODO: Notify users only in case of critical errors or if no valid content is found after crawling.
import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import aiofiles
import requests

from src.crawling.exceptions import JobNotCompletedError
from src.crawling.file_manager import FileManager
from src.crawling.job_manager import JobManager
from src.crawling.models import *
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field, HttpUrl, field_validator
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.utils.config import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_API_URL,
    RAW_DATA_DIR,
    JOB_FILE_DIR,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    WEBHOOK_URL, ENVIRONMENT, Environment,
)
from src.utils.decorators import base_error_handler, application_level_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


class FireCrawler:
    """
    A class for crawling and mapping URLs using the Firecrawl API.
    """

    def __init__(
        self,
            job_manager: JobManager,
            file_manager: FileManager,
            api_key: str = FIRECRAWL_API_KEY,
            api_url: str = FIRECRAWL_API_URL,
            data_dir: str = RAW_DATA_DIR,
            jobs_dir: str = JOB_FILE_DIR
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

        result = {
            "status": "success",
            "input_url": url,
            "total_links": total_links,
            "links": links,
            'method' : 'map'
        }

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
        params =  {
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
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(HTTPError),
        wait=wait_exponential(multiplier=1, min=30, max=300),
        before_sleep=lambda retry_state: logger.info(
            f"Retryable error occurred. Retrying in {retry_state.next_action.sleep} seconds..."
        ),
    )
    async def start_crawl(self, request: CrawlRequest) -> CrawlJob:
        """Start new crawl job"""
        # Build params with webhook
        params = self._build_params(request)
        if request.webhook_url:
            params["webhook"] = str(request.webhook_url)

        logger.debug(f"Crawl params: {params}")

        # Start FireCrawl job
        response = self.firecrawl_app.async_crawl_url(
            str(request.url),
            params
        )
        logger.info(f"Received response from FireCrawl: {response}")

        # Create tracked job
        job = await self.job_manager.create_job(
            firecrawl_id=response["id"],
            start_url=request.url
        )
        logger.info(f"Created job: {job.id} with start url: {job.start_url} and firecrawl id: {job.firecrawl_id}")

        return job

    @base_error_handler
    async def get_results(self, job_id: str) -> CrawlResult:
        """Get final results for completed job"""
        job = await self.job_manager.get_job(job_id)
        if not job or job.status != CrawlJobStatus.COMPLETED:
            raise JobNotCompletedError(f"Job {job_id} not complete")

        crawl_data = await self._accumulate_crawl_results(job.firecrawl_id)
        result = CrawlResult(
            job_status=job.status,
            input_url=str(job.start_url),
            total_pages=len(crawl_data),
            data=crawl_data
        )

        filename = await self.file_manager.save_result(result)
        job.result_file = filename
        await self.job_manager.update_job(job)
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
        crawl_data = CrawlData(data=[])

        while next_url:
            logger.info("Accumulating job results.")
            batch_data, next_url = await self._fetch_results_from_url(next_url)
            crawl_data.data.extend(batch_data["data"])

        logger.info("No more pages to fetch. Returning results")

        return crawl_data

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

    # TODO: refactor to use FileManager
    @base_error_handler
    async def save_result(self, result: CrawlResult) -> str:
        """
        Save results to a JSON file.

        Args:
            result (CrawlResult): The CrawlResult object to save.

        Returns:
            filename: str

        Raises:
            OSError: If there is an issue writing to the file.
        """
        filename = self._create_file_name(result.input_url, result.method)
        filepath = os.path.join(self.raw_data_dir, filename)

        async with aiofiles.open(filepath, 'w') as f:
            await f.write(result.model_dump_json(indent=2))
        return filepath

    @base_error_handler
    def _create_file_name(self, url: HttpUrl, method: str) -> str:
        """
        Generate a file name based on the URL and HTTP method.

        Args:
            url (HttpUrl): The URL to be parsed.
            method (str): The HTTP method used (e.g., 'GET', 'POST').

        Returns:
            str: A file name string derived from the URL and current timestamp.

        Raises:
            ValueError: If the URL is invalid.
        """
        parsed_url = urlparse(url)
        bare_url = parsed_url.netloc + parsed_url.path.rstrip("/")
        bare_url = re.sub(r"[^\w\-]", "_", bare_url)  # Replace non-word chars with underscore
        timestamp = self._get_timestamp()
        return f"{bare_url}_{timestamp}.json"


    @base_error_handler
    async def run_crawl_locally(self, request: CrawlRequest):
        """Run crawler with local polling"""

        # Create crawl request
        request = request

        logger.info(f"Running in {ENVIRONMENT} environment")
        logger.info(f"Using webhook URL: {request.webhook_url or 'None (polling mode)'}")

        try:
            # Start crawl
            start_time = datetime.now()
            logger.info(f"Starting crawl of {request.url}")

            job = await self.start_crawl(request)
            logger.info(f"Created job {job.id}")


            # Get results
            result = await self.get_results(job.id)
            end_time = datetime.now()

            # Log results
            logger.info(f"Crawl completed in {end_time - start_time}")
            logger.info(f"Pages crawled: {result.total_pages}")
            logger.info(f"Results saved to: {result.filename}")

        except Exception as e:
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
        jobs_dir=JOB_FILE_DIR
    )
    return crawler, job_manager



async def main():
    crawler, job_manager = await initialize_components()

    # Create crawl request
    request = CrawlRequest(
        url="https://docs.anthropic.com/en/",
        page_limit=1,
        exclude_patterns=["/blog/*"],
        include_patterns=["/docs/*"],
        # Use webhook URL based on environment
        webhook_url=WEBHOOK_URL if ENVIRONMENT != Environment.LOCAL else None
    )

    await crawler.run_crawl_locally(request)


if __name__ == "__main__":
    # Setup logging
    configure_logging(debug=True)

    # Run crawler
    asyncio.run(main())