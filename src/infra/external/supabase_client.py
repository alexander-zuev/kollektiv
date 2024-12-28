from supabase import AsyncClient, create_async_client

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class SupabaseClient:
    """Efficient Supabase client with immediate connection initialization."""

    def __init__(self, url: str = settings.supabase_url, key: str = settings.supabase_key) -> None:
        """Initialize Supabase client and connect immediately."""
        self.url = url
        self.key = key
        self._client: AsyncClient | None = None

    async def connect(self) -> None:
        """Connect to Supabase, handling potential errors."""
        if self._client is None:  # Only connect if not already connected
            try:
                logger.debug(
                    f"Attempting to connect to Supabase at: {self.url} with key partially masked as: {self.key[:5]}..."
                )
                self._client = await create_async_client(
                    supabase_url=self.url,
                    supabase_key=self.key,
                )
                logger.info("✓ Initialized Supabase client successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
                raise

    async def get_client(self) -> AsyncClient:
        """Get the connected client instance."""
        if self._client is None:
            await self.connect()
        return self._client
