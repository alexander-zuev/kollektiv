from urllib.parse import urlparse

import chromadb
from chromadb.api import AsyncClientAPI

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class ChromaClient:
    """Thin sync client for ChromaDB."""

    def __init__(self) -> None:
        """Initialize ChromaClient with the necessary dependencies."""
        self.client: AsyncClientAPI | None = None

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

    @classmethod
    async def create_client(cls) -> AsyncClientAPI:
        """Create a new Chroma client."""

        instance = cls()
        host, port = instance._parse_url(settings.chroma_private_url)
        try:
            instance.client = await chromadb.AsyncHttpClient(
                host=host,
                port=port,
                # settings=Settings(
                #     chroma_client_auth_provider="chromadb.auth.basic_authn.BasicAuthClientProvider",
                #     chroma_client_auth_credentials=settings.chroma_client_auth_credentials,
                # ),
            )
            await instance.client.heartbeat()
            logger.info(f"✓ Initialized Chroma client successfully on {settings.chroma_private_url}")
            return instance.client
        except Exception as e:
            logger.exception(f"Failed to initialize Chroma client: {str(e)}")
            raise
