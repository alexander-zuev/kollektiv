import json
import os
import time
from pydoc import html
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from pydantic import HttpUrl
from urllib.parse import urlparse
import re
from datetime import datetime
import requests
from requests.exceptions import RequestException

from firecrawl import FirecrawlApp

from src.utils.config import FIRECRAWL_API_KEY, NEW_RAW_DATA_DIR, NEW_JOB_FILE_DIR, SRC_ROOT
from src.utils.logger import setup_logger
from src.utils.decorators import error_handler

logger = setup_logger("firecrawler", "firecrawler.log")

class FireCrawler:
    def __init__(self, api_key: str, data_dir: str = NEW_RAW_DATA_DIR, jobs_dir: str = NEW_JOB_FILE_DIR) -> None:
        self.api_key: str = api_key
        self.logger = logger
        self.current_job_id: str
        self.raw_data_dir: str = data_dir
        self.jobs_dir: str = jobs_dir
        self.app = self._initialize_app()


    @error_handler(logger)
    def _initialize_app(self):
            app = FirecrawlApp(api_key=self.api_key)
            self.logger.info("FireCrawler app initialized successfully.")
            return app

    @error_handler(logger)
    def map_url(self, url: HttpUrl) -> Optional[Dict[str, Any]]:
        """Input a website and get all the urls on the website - extremely fast"""
        self.logger.info(f"Mapping URL: {url}")

        site_map = self.app.map_url(url)
        self.logger.info("Map results received. Attempting to parse the results.")

        # extract links and calculate total
        links = site_map
        total_links = len(links)

        self.logger.info(f"Total number of links received: {total_links}")

        result = {
            'status' : 'success',
            'input_url': url,
            'total_links': total_links,
            'links': links,
        }

        self.save_results(result, method="map")

        return result

    @error_handler(logger)
    def async_crawl_url(self, urls: List[HttpUrl], page_limit: int = 25) -> Dict[str, Any]:
        all_results = []

        for url in urls:
            params = {
                'limit': page_limit,
                'maxDepth': 5,
                "includePaths": ["/docs/*",
                                 '/api/*'],
                'scrapeOptions':
                    {'formats': ['markdown']}
            }

            self.logger.info(f"Starting crawl job for URL: {url} with page limit: {page_limit}")
            response = self.app.async_crawl_url(url, params)

            crawl_job_id = response['id'] # return the id from FireCrawl
            self.logger.info(f"Received job ID: {crawl_job_id}")

            # create a job with this id
            self.create_job(job_id=crawl_job_id, method="crawl", input_url=url)

            # check job status
            self.logger.info("***Polling job status***")
            job_status = self._poll_job_results(crawl_job_id)
            if job_status == 'failed':
                return {"status": "failed", "job_id": crawl_job_id}

            # get all the results
            crawl_results = self._get_all_crawl_results(crawl_job_id)
            unique_links = self._extract_unique_links(crawl_results)
            self.logger.info(f"Job {crawl_job_id} results received.")
            self.logger.info(f"Total data entries: {len(crawl_results)}, Unique links: {len(unique_links)}")

            # save the results
            crawl_results = {
                'input_url': url,
                'total_pages': len(crawl_results),
                'unique_links': unique_links,
                'data': crawl_results,
            }

            self.save_results(crawl_results, method="crawl")

            # complete the job
            self.complete_job(crawl_job_id)
            all_results.append(crawl_results)
        return {'input_urls': urls, 'results': all_results}

    @error_handler(logger)
    def _poll_job_results(self, job_id: str, attempts=None) -> str:
        while True:
            response = self.check_job_status(job_id)
            job_status = response['status']

            if job_status in ['completed', 'failed']:
                return job_status

            self.logger.info(f"Job {job_id} status: {job_status}. Retrying in 30 seconds...")
            time.sleep(30)

    @error_handler(logger)
    def _get_all_crawl_results(self,
                               job_id: str) -> List[Dict[str, Any]]:
        """ Fetch all results for a given crawl job, handling pagination"""
        next_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
        all_data = []

        while next_url:
            self.logger.info("Accumulating job results.")
            batch_data, next_url =  self._get_next_results(next_url)

            # process the first (or only) batch of data
            all_data.extend(batch_data['data'])

            if not next_url:
                self.logger.info("No more pages to fetch.")
                break # exit if no more pages to fetch

        return all_data

    @error_handler(logger)
    def _get_next_results(self, next_url: HttpUrl) -> Tuple[Dict[str, Any], Optional[str]]:
        """Retrieves the next batch of the results"""
        # how to implement re-tries? How to handle them gracefully?
        max_retries = 3
        backoff_factor = 2

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Trying to fetch the batch results for {next_url}")
                url = next_url
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers)
                batch_data = response.json()
                next_url = batch_data.get('next') # if it's missing -> there are no more pages to crawl
                return batch_data, next_url
            except RequestException as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to fetch results after {max_retries} attempts: {str(e)}")
                    raise
                else:
                    wait_time = backoff_factor ** attempt
                    self.logger.warning(f"Request failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        raise Exception("Failed to fetch results after maximum retries")

    @error_handler(logger)
    def save_results(self, result: Dict[str, Any], method: str) -> None:
        """Takes as an input the results of the job, saves it as a json file in the data directory"""
        filename = self._create_file_name(result['input_url'], method)
        filepath = os.path.join(self.raw_data_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)

        # build an example file
        self.build_example_file(filename)

        self.logger.info(f"Results saved to file: {filepath}")

    @error_handler(logger)
    def _create_file_name(self, url: HttpUrl, method: str) -> str:
        """Creates a slugified version of url + method for use as a file name"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.split('.')[0] # take only two parts of the domain
        path = parsed_url.path.strip('/').split('/')[0]

        # Combine parts and sanitize
        parts = [method[:3], domain, path] if path else [method[:3], domain]
        slug = '_'.join(parts)
        slug = re.sub(r'[^\w\-]', '', slug)  # Remove any non-word characters

        timestamp = self._get_timestamp()

        return f"{slug}_{timestamp}.json"

    @error_handler(logger)
    def _get_timestamp(self):
        """Returns the current timestamp to be used for saving the results"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @error_handler(logger)
    def create_job(self, job_id: str, method: str, input_url: HttpUrl) -> None:
        """Creates a job, saving information to jobs.json returned by async_crawl_url method."""
        internal_id = str(uuid4())
        path = os.path.join(self.jobs_dir, "jobs.json") # path should be src/crawling

        # create job info
        job_info = {
            'internal_id': internal_id,
            'job_id': job_id,
            'input_url' : input_url,
            'status' : 'started',
            'timestamp': self._get_timestamp(),
            'method' : method
        }

        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    jobs = json.load(f)
            else:
                jobs = {}

            # add a new jobs info
            jobs[internal_id] = job_info

            # write updated file to disk
            with open(path, 'w') as f:
                json.dump(jobs, f, indent=2)

            # update current job id
            self.current_job_id = internal_id

            self.logger.info(f"Created a job with firecrawl id: {job_id} and internal_id: {internal_id}")
        except IOError as e:
            self.logger.error(f"Error saving {job_id}: {e}")
            raise

    @error_handler(logger)
    def complete_job(self, job_id: str) -> None:
        """Finds a job by external id and updates it's status to "completed". """
        jobs_path = os.path.join(self.jobs_dir, "jobs.json")

        try:
            with open(jobs_path, 'r') as f:
                jobs = json.load(f)

            job_updated = False
            for internal_id, job_info in jobs.items():
                if job_info['job_id'] == job_id:
                    job_info['status'] = 'completed'
                    job_updated = True
                    break

            if not job_updated:
                raise ValueError(f"No job with id {job_id} found")

            with open(jobs_path, 'w') as f:
                json.dump(jobs, f, indent=2)

            self.logger.info(f"Job {job_id} marked as completed.")
        except IOError as e:
            self.logger.error(f"Error marking job {job_id} as completed: {e}")
            raise

    @error_handler(logger)
    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """Polls firecrawl for the job result"""
        response = self.app.check_crawl_status(job_id)
        self.logger.info(
            f"Job {job_id} status: {response['status']}. Completed: {response.get('completed', 'N/A')}/{response.get('total', 'N/A')}")
        return response

    @error_handler(logger)
    def _extract_unique_links(self, crawl_results: List[Dict[str, Any]]) -> List[str]:
        """ Extracts unique links in the completed crawl"""
        unique_links = set(item['metadata']['sourceURL'] for item in crawl_results if 'metadata' in item and 'sourceURL' in item['metadata'])
        return list(unique_links)

    @error_handler(logger)
    def build_example_file(self, filename: str, pages: int = 1) -> None:
        """Extracts n pages into example file to visualize its structure"""
        input_filename = filename
        input_filepath = os.path.join(self.raw_data_dir, input_filename)

        md_output_filename = "example.md"
        md_output_filepath = os.path.join(SRC_ROOT, 'data', 'example', md_output_filename)

        # ensure directory exists
        os.makedirs(os.path.dirname(md_output_filepath), exist_ok=True)

        with open(input_filepath, 'r') as f:
            json_data = json.load(f)

        with (open(md_output_filepath, 'w', encoding='utf-8') as md_file):
            for index, item in enumerate(json_data['data']):
                if index >= pages:
                    break

                # Markdown file
                if 'markdown' in item:
                    md_file.write(f"# Content for item {index}\n\n")
                    md_file.write(f"```markdown\n{item['markdown']}\n```\n\n")
                    md_file.write("----\n\n")

        logger.info(f"Example Markdown file created: {md_output_filepath}")

# Test usage
def main():
    crawler = FireCrawler(FIRECRAWL_API_KEY)

    # supabase_ai_map = crawler.map_url("https://supabase.com/docs/guides/ai")
    # print("Map results:")
    # print(f"Total number of links: {supabase_ai_map['total_links']}")
    # print("All links:")
    # print(supabase_ai_map['links'])

    # Testing crawl_url
    urls_to_crawl = ["https://docs.anthropic.com/en",
                    ]
    results = crawler.async_crawl_url(urls_to_crawl, page_limit=75)
    # crawler.build_example_file("cra_supabase_docs_2024-09-11 07:16:11.json")

if __name__ == "__main__":
    main()