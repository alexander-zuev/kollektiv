import json
from datetime import datetime
import aiofiles
import os
from typing import Tuple, Any
from urllib.parse import urlparse
import re

from src.crawling.models import CrawlResult


class FileReference:
    def __init__(self):
        self.filename = None
        self.filepath = None

# TODO: refactor to be a common / infra class
class FileManager:
    def __init__(self, raw_data_dir: str):
        self.raw_data_dir = raw_data_dir
        os.makedirs(self.raw_data_dir, exist_ok=True)

    def _create_filename(self, url: str, method: str) -> str:
        parsed_url = urlparse(url)
        bare_url = parsed_url.netloc + parsed_url.path.rstrip("/")
        bare_url = re.sub(r"[^\w\-]", "_", bare_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{bare_url}_{timestamp}.json"

    async def save_result(self, result: CrawlResult | Any) -> str:
        """Save crawl result and return filename"""
        filename = self._create_filename(result.input_url, result.method)
        filepath = os.path.join(self.raw_data_dir, filename)

        async with aiofiles.open(filepath, 'w') as f:
            await f.write(result.model_dump_json(indent=2))

        return filename

    async def load_result(self, filename: str) -> dict:
        """Load result file"""
        filepath = os.path.join(self.raw_data_dir, filename)
        async with aiofiles.open(filepath) as f:
            content = await f.read()
            return json.loads(content)