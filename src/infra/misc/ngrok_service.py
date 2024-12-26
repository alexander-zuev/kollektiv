import ngrok

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class NgrokService:
    """Ngrok service used to create a tunnel in local environment."""

    def __init__(self, ngrok_authtoken: str | None = settings.ngrok_authtoken):
        self.ngrok_authtoken = ngrok_authtoken

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
        logger.info("Disconnecting ngrok tunnel")
        ngrok.disconnect()
