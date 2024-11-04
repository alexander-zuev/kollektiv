import uuid
from datetime import UTC, datetime

from src.api.v0.content.schemas import (
    AddContentSourceRequest,
    ContentSourceResponse,
    ContentSourceStatus,
)
from src.core.content.crawler.crawler import FireCrawler
from src.infrastructure.config.logger import get_logger
from src.models.content.firecrawl_models import CrawlRequest

logger = get_logger()


class ContentService:
    def __init__(self, crawler: FireCrawler):
        self.crawler = crawler
        self._sources: dict[str, ContentSourceResponse] = {}  # In-memory storage for now

    async def add_source(self, request: AddContentSourceRequest) -> ContentSourceResponse:
        """Add a new content source and initiate crawling."""
        # 1. Create source first
        source = self._create_source(request)

        # 2. Store source locally
        self._sources[source.id] = source

        try:
            # 3. Map to FireCrawl config and start crawl job
            crawl_request = CrawlRequest(
                url=str(request.url),
                page_limit=request.config.max_pages,
                exclude_patterns=[p if p.startswith("/") else f"/{p}" for p in request.config.exclude_sections],
            )

            # Start crawl and store job ID
            job = await self.crawler.crawl(crawl_request)
            source.job_id = job.id  # Store FireCrawl job ID
            source.status = ContentSourceStatus.PROCESSING

            return source

        except Exception as e:
            logger.error(f"Failed to create crawl job: {e}")
            source.status = ContentSourceStatus.FAILED
            raise

        return source

    def _create_source(self, request: AddContentSourceRequest) -> ContentSourceResponse:
        """Create a new content source response."""
        source_id = str(uuid.uuid4())

        source = ContentSourceResponse(
            id=source_id,
            type=request.type,
            name=request.name,
            url=str(request.url),  # Convert HttpUrl to str
            status=ContentSourceStatus.PENDING,
            created_at=datetime.now(UTC),
            config=request.config,
        )

        return source
