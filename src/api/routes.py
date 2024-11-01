"""API route definitions."""

from typing import Final

# API version prefix
V0: Final = "/api/v0"


class Routes:
    """System routes (non-versioned)."""

    class System:
        """System routes (non-versioned)."""

        HEALTH = "/health"

        class Webhooks:
            """Webhook routes."""

            BASE = "/webhooks"
            FIRECRAWL = "/firecrawl"  # This will be combined with BASE in the router

    class Middleware:
        """Middleware routes."""

        AUTH = "/auth"

    # API routes (versioned)
    class V0:
        """API routes (versioned)."""

        BASE = V0

        # Feature endpoints
        CONTENT = f"{BASE}/content"
        CHAT = f"{BASE}/chat"

        class Content:
            """Content routes."""

            CRAWL = "/crawl"
            STATUS = "/status"
            DOCUMENTS = "/documents"

        class Chat:
            """Chat routes."""

            MESSAGE = "/message"
            STREAM = "/stream"
