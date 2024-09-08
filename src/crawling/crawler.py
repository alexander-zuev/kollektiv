import json
import os
import uuid
from typing import List, Dict, Any, Optional

from pydantic import HttpUrl
from urllib.parse import urlparse
import re
from datetime import datetime


from firecrawl import FirecrawlApp

from src.utils.config import FIRECRAWL_API_KEY, NEW_RAW_DATA_DIR
from src.utils.logger import setup_logger
from src.utils.decorators import error_handler

logger = setup_logger("firecrawler", "firecrawler.log")

class FireCrawler:
    def __init__(self, api_key: str, data_dir: str = NEW_RAW_DATA_DIR) -> None:
        self.api_key: str = api_key
        self.logger = logger
        self.current_job_id: uuid.UUID
        self.raw_data_dir: str = data_dir
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
    def crawl_url(self):
        pass

    @error_handler(logger)
    def save_results(self, result: Dict[str, Any], method: str) -> None:
        """Takes as an input the results of the job, saves it as a json file in the data directory"""
        filename = self._create_file_name(result['input_url'], method)
        filepath = os.path.join(self.raw_data_dir, filename)

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

# Test usage
crawler = FireCrawler(FIRECRAWL_API_KEY)
supabase_ai_map = crawler.map_url("https://supabase.com/docs/guides/ai")
print("Map results:")
print(f"Total number of links: {supabase_ai_map['total_links']}")
print("All links:")
print(supabase_ai_map['links'])