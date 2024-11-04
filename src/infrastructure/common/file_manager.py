import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import aiofiles

from src.models.content.firecrawl_models import CrawlResult


class FileReference:
    """Reference to a file."""

    def __init__(self):
        self.filename = None
        self.filepath = None


# TODO: refactor to be a common / infra class
class FileManager:
    """Manage file operations."""

    def __init__(self, raw_data_dir: str):
        self.raw_data_dir = raw_data_dir
        os.makedirs(self.raw_data_dir, exist_ok=True)

    def _create_filename(self, url: str, method: str) -> str:
        """Create standardized filename for results."""
        parsed_url = urlparse(url)
        bare_url = parsed_url.netloc + parsed_url.path.rstrip("/")
        bare_url = re.sub(r"[^\w\-]", "_", bare_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{bare_url}_{timestamp}.json"

    async def save_result(self, result: CrawlResult) -> str:
        """Save crawl result and return filename."""
        filename = self._create_filename(result.input_url, result.method)
        filepath = os.path.join(self.raw_data_dir, filename)

        # Update result with filename before saving
        result.filename = filename  # Set the filename in the result

        async with aiofiles.open(filepath, "w") as f:
            await f.write(result.model_dump_json(indent=2))

        return filename

    async def load_result(self, filename: str) -> dict:
        """Load result file."""
        filepath = os.path.join(self.raw_data_dir, filename)
        async with aiofiles.open(filepath) as f:
            content = await f.read()
            return json.loads(content)
