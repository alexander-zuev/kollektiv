from typing import Any
from uuid import UUID

import httpx
from firecrawl import FirecrawlApp
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

from src.core._exceptions import EmptyContentError, is_retryable_error
from src.infra.decorators import generic_error_handler, tenacity_retry_wrapper
from src.infra.logger import get_logger
from src.infra.settings import settings
from src.models.content_models import Document, DocumentMetadata
from src.models.firecrawl_models import (
    CrawlParams,
    CrawlRequest,
    FireCrawlResponse,
    ScrapeOptions,
)

logger = get_logger()


class FireCrawler:
    """
    A class for crawling and mapping URLs using the Firecrawl API.

    This class handles the interaction with the FireCrawl API, managing crawl jobs,
    and processing crawl results.

    Args:
        api_key (str, optional): FireCrawl API key. Defaults to FIRECRAWL_API_KEY.
        api_url (str, optional): FireCrawl API URL. Defaults to FIRECRAWL_API_URL.

    Attributes:
        api_key (str): The FireCrawl API key.
        api_url (str): The FireCrawl API base URL.
        firecrawl_app (FirecrawlApp): Instance of FireCrawl API client.
    """

    def __init__(
        self,
        api_key: str | None = settings.firecrawl_api_key,
        api_url: str = settings.firecrawl_api_url,
    ) -> None:
        if not api_key:
            raise ValueError("API key cannot be None")
        self.api_key: str = api_key
        self.api_url = api_url
        self.firecrawl_app = self.initialize_firecrawl()

    @generic_error_handler
    def initialize_firecrawl(self) -> FirecrawlApp:
        """Initialize and return the Firecrawl app."""
        app = FirecrawlApp(api_key=self.api_key)
        logger.info("✓ Initialized Firecrawler successfully")
        return app

    def _build_params(self, request: CrawlRequest) -> CrawlParams:
        """
        Build FireCrawl API parameters from a CrawlRequest.

        Args:
            request (CrawlRequest): The crawl request configuration

        Returns:
            CrawlParams: Parameters formatted for the FireCrawl API
        """
        # Handle webhook URL
        webhook_url = settings.firecrawl_webhook_url
        logger.debug(f"Using webhook URL: {webhook_url}")

        # Create and return CrawlParams
        params = CrawlParams(
            url=str(request.url),
            limit=request.page_limit,
            max_depth=request.max_depth,
            include_paths=request.include_patterns,
            exclude_paths=request.exclude_patterns,
            webhook=webhook_url,
            scrape_options=ScrapeOptions(),
        )

        return params

    @tenacity_retry_wrapper((HTTPError, Timeout, ConnectionError))
    async def start_crawl(self, request: CrawlRequest) -> FireCrawlResponse:
        """Start a new crawl job with webhook configuration."""
        try:
            params = self._build_params(request)
            logger.debug("Model configuration: %s", params)
            logger.debug("API payload: %s", params.dict())
            api_params = params.dict()

            response = self.firecrawl_app.async_crawl_url(str(request.url), api_params)
            firecrawl_response = FireCrawlResponse.from_firecrawl_response(response)
            logger.info(f"Received response from FireCrawl: {firecrawl_response}")
            return firecrawl_response
        except HTTPError as err:
            should_retry, _ = is_retryable_error(err)
            if should_retry:
                raise  # Let retry decorator handle it
            logger.exception(f"Non-retryable API error: {err}")
            raise
        except Timeout as err:
            logger.exception(f"Timeout fetching results from {request.url}: {err}")
            raise
        except RequestException as err:
            logger.exception(f"Connection error: {err}")
            raise

    async def get_results(self, firecrawl_id: str, source_id: UUID) -> list[Document]:
        """Get final results for a completed job.

        Args:
            firecrawl_id: The FireCrawl job ID
            source_id: UUID of DataSource object mapped to the crawl

        Returns:
            list[Document]: list of Document objects containing crawl results
        """
        next_url: str | None = f"https://api.firecrawl.dev/v1/crawl/{firecrawl_id}"
        documents: list[Document] = []

        while next_url is not None:
            logger.info("Accumulating job results.")
            batch_data, next_url = await self._fetch_results_from_url(next_url)

            # Extract new list of documents
            document_batch = self._get_documents_from_batch(batch=batch_data, source_id=source_id)
            documents.extend(document_batch)

        # Only checks at the end if data exists
        if not documents:
            logger.error(f"No data accumulated for job {firecrawl_id}")
            raise EmptyContentError(f"No content found for job {firecrawl_id}")

        logger.info(f"Accumulated {len(documents)} documents from firecrawl.")

        return documents

    def _get_documents_from_batch(self, batch: dict[str, Any], source_id: UUID) -> list[Document]:
        """Iterates over batch data and returns a list of documents."""
        document_batch: list[Document] = []

        for page in batch.get("data", []):
            if page.get("markdown"):
                # Get necessary data
                markdown_content = page.get("markdown")

                metadata = self._create_metadata(page)

                # Create Document
                document = Document(source_id=source_id, content=markdown_content, metadata=metadata)

                # Append to batch
                document_batch.append(document)
            else:
                logger.warning("Skipping page as it has no markdown content")

        return document_batch

    def _create_metadata(self, page: dict[str, Any]) -> DocumentMetadata:
        """Returns DocumentMetadata object based on data dict from firecrawl."""
        metadata = page.get("metadata")
        if metadata:
            return DocumentMetadata(
                title=metadata.get("title", ""),
                description=metadata.get("description", ""),
                source_url=metadata.get("sourceURL", ""),
                og_url=metadata.get("og:url", " "),
            )
        else:
            logger.warning("Metadata not found in page")
            return DocumentMetadata(title="", description="", source_url="", og_url="")

    @tenacity_retry_wrapper((HTTPError, Timeout, ConnectionError))
    async def _fetch_results_from_url(self, next_url: str) -> tuple[dict[str, Any], str | None]:
        """Fetch results with retries.

        Args:
            next_url: URL string for the next batch of results

        Returns:
            Tuple of (batch data dict, next URL string or None)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(next_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
                response.raise_for_status()

            batch_data = response.json()
            next_url = batch_data.get("next")  # This will be str | None
            return batch_data, next_url
        except HTTPError as err:
            logger.exception(f"HTTPError fetching results from {next_url}: {err}")
            raise
        except Timeout as err:
            logger.exception(f"Timeout fetching results from {next_url}: {err}")
            raise
        except ConnectionError as err:
            logger.exception(f"ConnectionError fetching results from {next_url}: {err}")
            raise
