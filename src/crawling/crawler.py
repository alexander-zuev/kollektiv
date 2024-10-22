# TODO: Improve the process flow
# TODO: Properly handle errors
# TODO: Allow users to retrieve the job results
# TODO: Implement validation for non-empty content during crawling to prevent passing empty pages to the chunker.
# TODO: Add checks for excluded URL patterns to ensure valid pages remain for processing after applying exclusions.
# TODO: Implement retries or error handling for pages that fail to be crawled (e.g., network errors).
# TODO: Provide more informative progress updates to the user during crawling (e.g., percentage completion).
# TODO: Notify users only in case of critical errors or if no valid content is found after crawling.
# TODO: Refactor job management
# TODO: Implement proper classes for CrawlInput and CrawlOutput
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field, HttpUrl, field_validator
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.utils.config import FIRECRAWL_API_KEY, JOB_FILE_DIR, RAW_DATA_DIR, SRC_ROOT
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


class CrawlRequest(BaseModel):
    """
    Represents a crawl request to FireCrawl.

    Validates and structures the input parameters for a crawl operation.
    """

    url: HttpUrl = Field(..., description="The starting URL of the crawl request.")
    page_limit: int = Field(..., gt=0, le=1000, description="Maximum number of pages to crawl. Maxium")
    max_depth: int = Field(
        default=5, gt=0, le=10, description="Maximum depth for crawling"  # Move from hardcoded in async_crawl_url
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="The list of str of patterns to "
        "exclude. For "
        "example, "
        "/blog/*, /author/. Delimited by a comma",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="The list of str of patterns to "
        "include. For "
        "example, "
        "/blog/*, /api/. Delimited by a comma",
    )

    @field_validator("url")
    def url_must_be_http_url(cls, v):
        try:
            HttpUrl(v)
            return v
        except Exception as e:
            raise ValueError("Invalid URL. It should start with 'http://' or 'https://'.") from e

    @field_validator("exclude_patterns", "include_patterns")
    def validate_patterns(cls, v: list[str]) -> list[str]:
        """Validate URL patterns are properly formatted."""
        for pattern in v:
            if not pattern.strip():
                raise ValueError("Empty patterns are not allowed")
            if not pattern.startswith("/"):
                raise ValueError("Pattern must start with '/', got: {pattern}")
        return v

    class Config:
        arbitrary_types_allowed = True


class CrawlData(BaseModel):
    """
    Represents the crawled data from a single page.

    Maintains compatibility with FireCrawl's output structure.
    """

    data: list[dict[str, Any]] = Field(..., description="List of page data objects from FireCrawl")

    @field_validator("data")
    def validate_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("Data must not be empty")
        for item in v:
            if not isinstance(item, dict):
                raise ValueError(f"Expected dict, got {type(item)}")
            if "markdown" not in item:
                raise ValueError("Missing 'markdown' key in data")
            if "metadata" not in item:
                raise ValueError("Missing 'metadata' key in data")
            if item["markdown"] is None:
                raise ValueError("Markdown cannot be None")
        return v


class CrawlJobStatus(str, Enum):
    """Add proper status enum instead of free-form string"""

    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


class CrawlResult(BaseModel):
    """
    Represents the complete result of a crawl operation.

    Maintains compatibility with your existing result structure while adding
    validation and proper typing.
    """

    job_status: CrawlJobStatus = Field(...)
    input_url: str = Field(..., description="The original URL that was crawled")
    total_pages: int = Field(..., ge=0, description="Total number of pages successfully crawled")
    unique_links: list[str] = Field(default_factory=list, description="List of unique URLs discovered during crawling")
    data: list[CrawlData] = Field(..., description="The actual crawled data from all pages")
    completed_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="When the crawl job completed"
    )
    error_message: str | None = Field(None, description="Error message if the crawl failed")

    @field_validator("data")
    def validate_data_length(cls, v: list[CrawlData], values: dict) -> list[CrawlData]:
        """Ensure total_pages matches data length"""
        if len(v) != values.get("total_pages", 0):
            raise ValueError(f"Data length {len(v)} does not match total_pages {values.get('total_pages')}")
        return v

    class Config:
        # Allows converting datetime to ISO format in JSON
        json_encoders = {datetime: lambda v: v.isoformat()}

        # Allows extra fields in input data
        extra = "allow"

        # Validates whenever a field is set
        validate_assignment = True


class CrawlJob:
    pass


class CrawlJobStats(BaseModel):
    pass


class FireCrawler:
    """
    FireCrawler class for mapping and crawling URLs using the Firecrawl API.

    Args:
        api_key (str): The API key for authenticating with the Firecrawl service.
        data_dir (str): The directory where raw data is stored. Default is RAW_DATA_DIR.
        jobs_dir (str): The directory where job files are stored. Default is JOB_FILE_DIR.
    """

    def __init__(
        self, api_key: str = FIRECRAWL_API_KEY, data_dir: str = RAW_DATA_DIR, jobs_dir: str = JOB_FILE_DIR
    ) -> None:
        self.api_key: str = api_key
        self.current_job_id: str
        self.raw_data_dir: str = data_dir
        self.jobs_dir: str = jobs_dir
        self.app = self._initialize_app()

    @base_error_handler
    def _initialize_app(self):
        app = FirecrawlApp(api_key=self.api_key)
        logger.info("FireCrawler app initialized successfully.")
        return app

    # TODO: refactor into proper classes
    @base_error_handler
    def map_url(self, url: HttpUrl) -> dict[str, Any] | None:
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

        site_map = self.app.map_url(url)
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
        }

        filepath, filename = self.save_results(result, method="map")

        return result

    @staticmethod
    def is_retryable_error(exception):
        """Return True if the exception is an HTTPError with a status code we want to retry."""
        if isinstance(exception, HTTPError):
            return exception.response.status_code in [429, 500, 502, 503, 504]
        return False

    def crawl_handler(self, urls: list[HttpUrl]) -> dict[str, Any] | None:
        """Handles the crawl request -> ei"""

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(HTTPError),
        wait=wait_exponential(multiplier=1, min=30, max=300),
        before_sleep=lambda retry_state: logger.info(
            f"Retryable error occurred. Retrying in {retry_state.next_action.sleep} seconds..."
        ),
    )
    @base_error_handler
    async def async_crawl_url(self, crawl_request: CrawlRequest) -> dict[str, Any]:
        """
        Crawl multiple URLs asynchronously and retrieve results.

        Args:
            crawl_request (CrawlRequest): A CrawlRequest instance.

        Returns:
            dict: A dictionary containing the input URLs and the corresponding crawl results.

        Raises:
            HTTPError: If an HTTP error occurs and is determined to be retryable.
        """

        url = str(crawl_request.url)
        page_limit = crawl_request.page_limit
        exclude_patterns = crawl_request.exclude_patterns
        include_patterns = crawl_request.include_patterns


        params = {
            "limit": page_limit,
            "maxDepth": 5,
            "includePaths": include_patterns if include_patterns else [],
            "excludePaths": exclude_patterns if exclude_patterns else [],
            "scrapeOptions": {
                "formats": [
                    "markdown",
                ],
                "excludeTags": ["img"],  # remove images as Kollektiv doesn't support multi-modal embeddings
            },
        }

        logger.info(f"Starting crawl job for URL: {url} with page limit: {page_limit}")
        try:
            response = self.app.async_crawl_url(url, params)
            crawl_job_id = response["id"]  # return the id from FireCrawl
            logger.info(f"Received job ID: {crawl_job_id}")

            # create a job with this id
            self.create_job(job_id=crawl_job_id, method="crawl", input_url=url)

            # check job status
            job_failed = False
            logger.info("***Polling job status***")
            job_status = self._poll_job_results(crawl_job_id)
            if job_status == "failed":
                # return {"status": "failed", "job_id": crawl_job_id}
                logger.warning(f"Job {crawl_job_id} failed. Attempting to retrieve partial results.")
                job_failed = True

            # get all the results
            crawl_results = self._get_all_crawl_results(crawl_job_id)
            unique_links = self._extract_unique_links(crawl_results)
            logger.info(f"Job {crawl_job_id} results received.")
            logger.info(f"Total data entries: {len(crawl_results)}, Unique links: {len(unique_links)}")

            # save the results
            crawl_result = CrawlResult(
                job_status=job_status,
                input_url=url,
                total_pages=len(crawl_results),
                unique_links=unique_links,
                data=crawl_results,
            )

            crawl_results = {
                "job_failed": job_failed,
                "input_url": url,
                "total_pages": len(crawl_results),
                "unique_links": unique_links,
                "data": crawl_results,
            }

            filepath, filename = self.save_results(crawl_results, method="crawl")

            # complete the job
            self.complete_job(crawl_job_id)

            return {"input_urls": url, "results": crawl_results, "filename": filename}

        except HTTPError as e:
            logger.warning(f"Received HTTPError while crawling {url}: {e}")
            if self.is_retryable_error(e):
                raise  # raise to the decorator to handle
            else:
                logger.error(f"HTTPError occurred while crawling {url}: {e}")
                # Handle other HTTP errors without retrying

    @base_error_handler
    def _poll_job_results(self, job_id: str, attempts=None) -> str:
        while True:
            response = self.check_job_status(job_id)
            job_status = response["status"]

            if job_status in ["completed", "failed"]:
                return job_status

            logger.info(f"Job {job_id} status: {job_status}. Retrying in 30 seconds...")
            time.sleep(30)

    @base_error_handler
    def _get_all_crawl_results(self, job_id: str) -> list[dict[str, Any]]:
        """
        Accumulate all crawling results for a given job ID.

        Args:
            job_id (str): The unique identifier of the crawling job.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing the accumulated crawl results.

        Raises:
            SomeSpecificException: Description of the exception if applicable.
        """
        next_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
        all_data = []

        while next_url:
            logger.info("Accumulating job results.")
            batch_data, next_url = self._get_next_results(next_url)

            # process the first (or only) batch of data
            all_data.extend(batch_data["data"])

            if not next_url:
                logger.info("No more pages to fetch.")
                break  # exit if no more pages to fetch

            # IT'S A NEW WAY, IT'S A NEW LIFE
            data = CrawlData(data=(batch_data))

        return all_data

    @base_error_handler
    def _get_next_results(self, next_url: HttpUrl) -> tuple[dict[str, Any], str | None]:
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
        max_retries = 15
        backoff_factor = 2

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
    def save_results(self, result: dict[str, Any], method: str) -> str:
        """
        Save results to a JSON file and build an example file.

        Args:
            result (dict[str, Any]): The result data to save.
            method (str): The method used to generate the result.

        Returns:
            None

        Raises:
            OSError: If there is an issue writing to the file.
        """
        filename = self._create_file_name(result["input_url"], method)
        filepath = os.path.join(self.raw_data_dir, filename)

        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)

        # build an example file
        self.build_example_file(filename)

        logger.info(f"Results saved to file: {filepath}")

        return filepath, filename

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
    def _get_timestamp(self):
        """
        Generate a timestamp string in the format YYYYMMDD_HHMMSS.

        Returns:
            str: The current timestamp in the format YYYYMMDD_HHMMSS.
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @base_error_handler
    def create_job(self, job_id: str, method: str, input_url: HttpUrl) -> None:
        """
        Create a new job with the given parameters and save it to disk.

        Args:
            job_id (str): The unique identifier for the job.
            method (str): The method to be used for the job.
            input_url (HttpUrl): The URL associated with the job.

        Raises:
            OSError: If there is an error saving the job information to disk.
        """
        internal_id = str(uuid4())
        path = os.path.join(self.jobs_dir, "jobs.json")  # path should be src/crawling

        # create job info
        job_info = {
            "internal_id": internal_id,
            "job_id": job_id,
            "input_url": input_url,
            "status": "started",
            "timestamp": self._get_timestamp(),
            "method": method,
        }

        try:
            if os.path.exists(path):
                with open(path) as f:
                    jobs = json.load(f)
            else:
                jobs = {}

            # add a new jobs info
            jobs[internal_id] = job_info

            # write updated file to disk
            with open(path, "w") as f:
                json.dump(jobs, f, indent=2)

            # update current job id
            self.current_job_id = internal_id

            logger.info(f"Created a job with firecrawl id: {job_id} and internal_id: {internal_id}")
        except OSError as e:
            logger.error(f"Error saving {job_id}: {e}")
            raise

    @base_error_handler
    def complete_job(self, job_id: str) -> None:
        """
        Mark a job with the given ID as completed.

        Args:
            job_id (str): The ID of the job to be marked as completed.

        Raises:
            ValueError: If no job with the specified job_id is found.
            OSError: If there is an error in reading or writing the jobs file.
        """
        jobs_path = os.path.join(self.jobs_dir, "jobs.json")

        try:
            with open(jobs_path) as f:
                jobs = json.load(f)

            job_updated = False
            for _internal_id, job_info in jobs.items():
                if job_info["job_id"] == job_id:
                    job_info["status"] = "completed"
                    job_updated = True
                    break

            if not job_updated:
                raise ValueError(f"No job with id {job_id} found")

            with open(jobs_path, "w") as f:
                json.dump(jobs, f, indent=2)

            logger.info(f"Job {job_id} marked as completed.")
        except OSError as e:
            logger.error(f"Error marking job {job_id} as completed: {e}")
            raise

    @base_error_handler
    def check_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Check the status of a job.

        Args:
            job_id (str): The unique identifier of the job.

        Returns:
            dict[str, Any]: A dictionary containing the job status and other related information.

        Raises:
            KeyError: If the response does not contain the required status information.
        """
        response = self.app.check_crawl_status(job_id)
        logger.info(
            f"Job {job_id} status: {response['status']}."
            f" Completed: {response.get('completed', 'N/A')}/{response.get('total', 'N/A')}"
        )
        return response

    @base_error_handler
    def _extract_unique_links(self, crawl_results: list[dict[str, Any]]) -> list[str]:
        """
        Extract unique source URLs from crawl results.

        Args:
            crawl_results (list[dict[str, Any]]): A list of dictionaries containing crawl results.

        Returns:
            list[str]: A list of unique source URLs extracted from the crawl results.

        Raises:
            KeyError: If the 'metadata' or 'sourceURL' key is missing in any of the dictionaries.
        """
        unique_links = {
            item["metadata"]["sourceURL"]
            for item in crawl_results
            if "metadata" in item and "sourceURL" in item["metadata"]
        }
        return list(unique_links)

    @base_error_handler
    def build_example_file(self, filename: str, pages: int = 1) -> None:
        """
        Build an example Markdown file from input JSON.

        Args:
            filename (str): The name of the input JSON file.
            pages (int, optional): The number of pages to include in the output Markdown file. Defaults to 1.

        Raises:
            FileNotFoundError: If the input JSON file does not exist.
            json.JSONDecodeError: If the input file is not a valid JSON.
            OSError: If there is an error in writing the output file.

        """
        input_filename = filename
        input_filepath = os.path.join(self.raw_data_dir, input_filename)

        md_output_filename = "example.md"
        md_output_filepath = os.path.join(SRC_ROOT, "data", "example", md_output_filename)

        # ensure directory exists
        os.makedirs(os.path.dirname(md_output_filepath), exist_ok=True)

        with open(input_filepath) as f:
            json_data = json.load(f)

        with open(md_output_filepath, "w", encoding="utf-8") as md_file:
            for index, item in enumerate(json_data["data"]):
                if index >= pages:
                    break

                # Markdown file
                if "markdown" in item:
                    md_file.write(f"# Content for item {index}\n\n")
                    md_file.write(f"```markdown\n{item['markdown']}\n```\n\n")
                    md_file.write("----\n\n")

        logger.info(f"Example Markdown file created: {md_output_filepath}")


# Test usage
async def main():
    """Run crawler as a script. Initiates logger separately."""
    configure_logging(debug=True)
    crawler = FireCrawler(FIRECRAWL_API_KEY)

    # Crawling documentation
    urls_to_crawl = [
        "https://docs.ragas.io/en/stable/",  # replace this
    ]
    exclude_patterns = ["/blog/*", "/author/"]
    # include_patterns = []

    crawl_request = CrawlRequest(
        url="https://docs.ragas.io/en/stable/",
        page_limit=1,
        exclude_patterns=exclude_patterns,
        # include_patterns=include_patterns
    )

    await crawler.async_crawl_url(crawl_request)


if __name__ == "__main__":
    asyncio.run(main())