import uuid
from typing import List, Dict, Any

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
    def map_url(self, url) -> List[str]:
        """Input a website and get all the urls on the website - extremely fast"""
        site_map = self.app.map_url(url)
        return site_map

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