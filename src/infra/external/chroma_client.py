from urllib.parse import urlparse

import chromadb
from chromadb.api import ClientAPI

from src.infra.logger import get_logger
from src.infra.settings import Environment, settings
from chromadb import Settings

logger = get_logger()


class ChromaClient:
    """Thin sync client for ChromaDB."""

    def __init__(self) -> None:
        """Initialize ChromaClient with the necessary dependencies."""
        # self.client: AsyncClientAPI | None = None
        self.client: ClientAPI | None = None

    @classmethod
    def create_client(cls) -> "ChromaClient":
        """Create a new Chroma client."""

        url_parts = urlparse(settings.chroma_private_url)
        host = url_parts.hostname
        port = url_parts.port
        logger.debug(f"Initializing Chroma client using URL: {settings.chroma_private_url}")

        instance = cls()

        try:
            if settings.environment == Environment.LOCAL:
                # instance.client = await chromadb.AsyncHttpClient(host=host, port=port)
                instance.client = chromadb.HttpClient(host=host, port=port)
            elif settings.environment in [Environment.STAGING, Environment.PRODUCTION]:
                logger.debug(f"Initializing Chroma client using host: {host} and port: {port} with auth credentials")
                if not settings.chroma_client_auth_credentials:
                    raise ValueError("CHROMA_CLIENT_AUTH_CREDENTIALS must be set in staging/production")

                # instance.client = await chromadb.AsyncHttpClient(
                instance.client = chromadb.HttpClient(
                    host=host,
                    port=port,
                    settings=Settings(
                        chroma_client_auth_provider="chromadb.auth.basic_authn.BasicAuthClientProvider",
                        chroma_client_auth_credentials=settings.chroma_client_auth_credentials,
                    ),
                    # headers={"Authorization": f"Basic {settings.chroma_client_auth_credentials}"},
                )
            # await instance.client.heartbeat()
            instance.client.heartbeat()
            logger.info("✓ Initialized Chroma client successfully")
            return instance
        except Exception as e:
            logger.error(f"Failed to initialize Chroma client: {str(e)}", exc_info=True)
            raise
