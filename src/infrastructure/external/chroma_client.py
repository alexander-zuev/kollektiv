from urllib.parse import urlparse

import chromadb
from chromadb.api.async_api import AsyncClientAPI
from chromadb.config import Settings

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import Environment, settings

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

        if settings.environment == Environment.LOCAL:
            instance.client = await chromadb.AsyncHttpClient(host=host, port=port)
        elif settings.environment in [Environment.STAGING, Environment.PRODUCTION]:
            logger.info(f"Initializing Chroma client using host: {host} and port: {port} with auth credentials")
            if not settings.chroma_client_auth_credentials:
                raise ValueError("CHROMA_CLIENT_AUTH_CREDENTIALS must be set in staging/production")

            instance.client = await chromadb.AsyncHttpClient(
                host=host,
                port=port,
                settings=Settings(
                    chroma_client_auth_provider="chromadb.auth.basic_authn.BasicAuthClientProvider",
                    chroma_client_auth_credentials=settings.chroma_client_auth_credentials,
                ),
                headers={"Authorization": f"Bearer {settings.chroma_client_auth_credentials}"},
            )
        await instance.client.heartbeat()
        return instance
