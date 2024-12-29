import ngrok

from src.infra.logger import get_logger
from src.infra.settings import settings
from src.models.base_models import Environment

logger = get_logger()


class NgrokService:
    """Ngrok service used to create a tunnel in local environment."""

    def __init__(self, ngrok_authtoken: str | None = settings.ngrok_authtoken):
        self.ngrok_authtoken = ngrok_authtoken

    @classmethod
    async def create(cls, ngrok_authtoken: str | None = settings.ngrok_authtoken) -> "NgrokService":
        """Creates an instance of NgrokService."""
        if settings.environment == Environment.LOCAL:
            instance = cls(ngrok_authtoken=ngrok_authtoken)
            await instance.start_tunnel()
            return instance
        logger.info("✓ Skipping ngrok tunnel initialization for non-local environment")
        return None

    async def start_tunnel(self) -> str:
        """Start the ngrok tunnel and return the listener."""
        try:
            listener = await ngrok.forward(addr=f"localhost:{settings.api_port}", authtoken=self.ngrok_authtoken)
            settings.ngrok_url = listener.url()
            logger.info(f"✓ Initialized ngrok tunnel successfully at: {settings.ngrok_url}")
            return settings.ngrok_url
        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {e}")
            raise e

    async def stop_tunnel(self) -> None:
        """Stop the ngrok tunnel."""
        try:
            ngrok.disconnect()
            logger.info("Disconnecting ngrok tunnel")
        except Exception as e:
            logger.error(f"Failed to disconnect ngrok tunnel: {e}")
            raise e
