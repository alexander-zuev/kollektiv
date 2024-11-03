import uuid
from datetime import UTC, datetime

from src.api.v0.content.schemas import (
    AddContentSourceRequest,
    ContentSourceResponse,
    ContentSourceStatus,
)
from src.core.content.crawler.crawler import FireCrawler
from src.infrastructure.config.logger import get_logger

logger = get_logger()


class ContentService:
    def __init__(self, crawler: FireCrawler):
        self.crawler = crawler
        self._sources: dict[str, ContentSourceResponse] = {}  # In-memory storage for now

    async def add_source(self, request: AddContentSourceRequest) -> ContentSourceResponse:
        """Add a new content source and initiate crawling."""
        source_id = str(uuid.uuid4())

        # Create source response
        source = ContentSourceResponse(
            id=source_id,
            type=request.type,
            name=request.name,
            url=str(request.url),  # Convert HttpUrl to str
            status=ContentSourceStatus.PENDING,
            created_at=datetime.now(UTC),
            config=request.config,
        )

        # Store source
        self._sources[source_id] = source

        # Start crawl job
        try:
            await self.crawler.create_crawl_job(url=str(request.url), config=request.config)
        except Exception as e:
            logger.error(f"Failed to create crawl job: {e}")
            source.status = ContentSourceStatus.FAILED
            raise

        return source
