"""API route definitions."""

from typing import Final

# API version prefix
V0_PREFIX: Final = "/api/v0"  # Rename for clarity


class Routes:
    """API route definitions."""

    class System:
        """System routes (non-versioned)."""

        HEALTH = "/health"

        class Webhooks:
            """Webhook routes."""

            BASE = "/webhooks"
            FIRECRAWL = f"{BASE}/firecrawl"

    class V0:  # Use lowercase for consistency with prefix
        """API routes (versioned)."""

        CONTENT = "/content"
        CHAT = "/chat"

        class Content:
            """Content management routes."""

            SOURCES = "/sources"
            SOURCE = "/sources/{source_id}"
            SOURCE_STATUS = "/sources/{source_id}/status"

        class Chat:
            """Chat routes."""

            MESSAGE = "/message"
            STREAM = "/stream"
