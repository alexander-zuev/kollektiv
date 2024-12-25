from urllib.parse import urlparse

import chromadb
from chromadb.api.async_api import AsyncClientAPI

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings

logger = get_logger()


class ChromaClient:
    """Thin async client for ChromaDB."""

    def __init__(self) -> None:
        """Initialize ChromaClient with the necessary dependencies."""
        self.client: AsyncClientAPI | None = None

    @classmethod
    async def create_client(cls, host: str = settings.chroma_host, port: int = settings.chroma_port) -> "ChromaClient":
        """Create a new asyncChroma client."""
        if settings.chroma_url:
            url_parts = urlparse(settings.chroma_url)
            host = url_parts.hostname
            port = url_parts.port
            logger.info(f"Initializing Chroma client using URL: {settings.chroma_url}")
        else:
            logger.info(
                f"Initializing Chroma client using host: {settings.chroma_host} and port: {settings.chroma_port}"
            )
            host = settings.chroma_host
            port = settings.chroma_port

        instance = cls()
        instance.client = await chromadb.AsyncHttpClient(host=host, port=port)
        await instance.client.heartbeat()
        return instance
