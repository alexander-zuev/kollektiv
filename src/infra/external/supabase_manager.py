import tenacity
from supabase import AsyncClient, create_async_client

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class SupabaseManager:
    """Efficient Supabase client manager with immediate connection and retrying logic."""

    def __init__(
        self, supabase_url: str = settings.supabase_url, service_role_key: str = settings.supabase_service_role_key
    ) -> None:
        """Initialize Supabase client and connect immediately."""
        self.supabase_url = supabase_url
        self.service_role_key = service_role_key
        self._client: AsyncClient | None = None  # instance of Supabase async client

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=15),
        retry=tenacity.retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Supabase connection attempt {retry_state.attempt_number} failed. Retrying..."
        ),
    )
    async def _connect_async(self) -> None:
        """Connect to Supabase, retry if connection fails."""
        if self._client is None:
            try:
                logger.debug(
                    f"Attempting to connect to Supabase at: {self.supabase_url} with key partially masked as:"
                    f"{self.service_role_key[:5]}..."
                )
                self._client = await create_async_client(
                    supabase_url=self.supabase_url,
                    supabase_key=self.service_role_key,
                )
                logger.info("✓ Initialized Supabase client successfully")
            except Exception as e:
                logger.exception(f"Failed to initialize Supabase client: {e}")
                raise

    @classmethod
    async def create(cls) -> "SupabaseManager":
        """Factory method to elegantly create a Supabase client instance and connect immediately."""
        instance = cls()
        await instance._connect_async()
        return instance

    async def get_client(self) -> AsyncClient:
        """Wrapper method to get the connected client instance or reconnect if necessary."""
        await self._connect_async()
        return self._client
