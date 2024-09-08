import uuid
from typing import List, Dict, Any, Optional
from pydantic import HttpUrl

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

        return result

    @error_handler(logger)
    def crawl_url(self):
        pass

    def save_results(self, results: List[str]) -> None:
        """Takes as an input the results of the job, saves it as a json file in the data directory"""
        pass

    def _create_file_name(self):
        """Creates a slugified version of url + method for use as a file name"""
        pass

    def _get_timestamp(self):
        """Returns the current timestamp to be used for saving the results"""
        pass

# Test usage
crawler = FireCrawler(FIRECRAWL_API_KEY)
supabase_ai_map = crawler.map_url("https://supabase.com/docs/guides/ai")
print("Map results:")
print(f"Total number of links: {supabase_ai_map['total_links']}")
print("All links:")
print(supabase_ai_map['links'])