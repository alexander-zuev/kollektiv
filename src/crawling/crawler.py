import json
import os
import uuid
import time
from typing import List, Dict, Any, Optional
from uuid import uuid4

from pydantic import HttpUrl
from urllib.parse import urlparse
import re
from datetime import datetime
import requests

from firecrawl import FirecrawlApp

from src.utils.config import FIRECRAWL_API_KEY, NEW_RAW_DATA_DIR, NEW_JOB_FILE_DIR
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
    def async_crawl_url(self, url: HttpUrl, params: Dict[str, Any]) -> str:
        response = self.app.async_crawl_url(url, params)
        job_id = response['id'] # return the id from FireCrawl

        # create a job with this id
        self.create_job(job_id=job_id, method="crawl")

        # poll until the results are received
        while True:
            response = self.check_job_status(job_id)
            job_status = response['status']
            if job_status == 'completed':
                results = self._get_all_crawl_results(job_id)
                break
            if job_status == 'failed':
                self.logger.error(f"Crawling job failed, ID: {job_id}")
                return f"Job {job_id} failed"
            self.logger.info("Re-checking in 30 seconds...")
            time.sleep(30)

        # save the results
        self.save_results(results, method="crawl")

        # complete the job
        self.complete_job(job_id)
        return f"Job {job_id} completed successfully."

    def _get_all_crawl_results(self, job_id: str) -> Dict[str, Any]:
        """ Fetch all results for a given crawl job, handling pagination """
        all_data = []
        next_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
        completed_pages = 0

        while next_url:
            partial_results = self._get_next_results(next_url)
            all_data.extend(partial_results['data'])
            completed_pages += len(partial_results['data'])
            total_pages = partial_results['total']

            next_url = partial_results.get('next')
            self.logger.info(f"Fetched {completed_pages}/{total_pages} pages")

            if next_url:
                time.sleep(1)  # Respect rate limits

        return {
            'data': all_data
        }

    def _get_next_results(self, job_id: str,) -> Dict[str, Any]:
        """Fetch the nezt batch of results form the given job_id"""
        max_retries = 3
        backoff_factor = 2

        url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.request("GET", url, headers=headers)
        partial_results = {
            'completed' : response['completed'],
            'total' : response['total'],
            'data' : response['data']
        }
        pct_remaining = response['completed'] / response['total']
        self.logger.info(f"Remaining {pct_remaining}%")
        return partial_results


    @error_handler(logger)
    def save_results(self, result: Dict[str, Any], method: str) -> None:
        """Takes as an input the results of the job, saves it as a json file in the data directory"""
        filename = self._create_file_name(result['input_url'], method)
        filepath = os.path.join(self.raw_data_dir, filename)

        if method == 'crawl':
            metadata = {
                'input_url': result['input_url'],
                'total_links': result['total_links'],
            }
            data = result['data']
            result = {
                'metadata': metadata,
                'data': data
            }

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)

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
        return datetime.now().strftime("%y%m%d_%H%M%S")

    @error_handler(logger)
    def create_job(self, job_id: str, method: str) -> None:
        """Creates a job, saving information to jobs.json returned by async_crawl_url method."""
        internal_id = str(uuid4())
        path = os.path.join(self.jobs_dir, "jobs.json") # path should be src/crawling

        # create job info
        job_info = {
            'internal_id': internal_id,
            'job_id': job_id,
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

            self.logger.info(f"Job ID {job_id} saved successfully with internal ID {internal_id}")
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
    def check_job_status(self, job_id: str) -> None:
        """Polls firecrawl for the job result"""
        response = self.app.check_crawl_status(job_id)
        logger.info(f"Status for job {job_id}: {response['status']}")
        return response


# Test usage
crawler = FireCrawler(FIRECRAWL_API_KEY)
# supabase_ai_map = crawler.map_url("https://supabase.com/docs/guides/ai")
# print("Map results:")
# print(f"Total number of links: {supabase_ai_map['total_links']}")
# print("All links:")
# print(supabase_ai_map['links'])

# Testing crawl_url
url_to_crawl = "https://supabase.com/docs/guides/ai"
crawl_status=crawler.app.async_crawl_url(
    url=url_to_crawl,
    params={
        'limit' : 2,
        'scrapeOptions': {'formats': ['markdown',]}

    },
)
print(crawl_status)