from urllib.parse import urlparse

import chromadb
from chromadb.api import AsyncClientAPI

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class ChromaManager:
    """Chroma client manager."""

    def __init__(self) -> None:
        """Initialize ChromaManager with the necessary dependencies."""
        self._client: AsyncClientAPI | None = None

    @staticmethod
    def _parse_url(url: str) -> tuple[str, int]:
        """Parse the URL to get the host and port."""
        try:
            url_parts = urlparse(url)
            host = url_parts.hostname
            port = url_parts.port
            return host, port
        except Exception as e:
            logger.error(f"Failed to parse URL: {str(e)}", exc_info=True)
            raise

    @tenacity_retry_wrapper()
    async def _connect_async(self) -> None:
        """Connect to ChromaDB."""
        host, port = self._parse_url(settings.chroma_private_url)
        if self._client is None:
            try:
                self._client = await chromadb.AsyncHttpClient(
                    host=host,
                    port=port,
                )
                await self._client.heartbeat()
                logger.info(f"✓ Initialized Chroma client successfully on {settings.chroma_private_url}")
            except Exception as e:
                logger.exception(f"Failed to initialize Chroma client: {str(e)}")
                raise

    @classmethod
    async def create_async(cls) -> "ChromaManager":
        """Create a new ChromaManager instance and connect to ChromaDB."""
        instance = cls()
        if instance._client is None:
            await instance._connect_async()
        return instance

    async def get_async_client(self) -> AsyncClientAPI:
        """Get the async client, reconnect if not connected."""
        await self._connect_async()
        return self._client
