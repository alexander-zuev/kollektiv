"""API route definitions."""

from typing import Final

# API version prefix
V0_PREFIX: Final = "/api/v0"  # Rename for clarity


class Routes:
    """API route definitions."""

    class System:
        """System routes (non-versioned)."""

        HEALTH = "/health"
        SENTRY_DEBUG = "/sentry-debug"

        class Webhooks:
            """Webhook routes."""

            BASE = "/webhooks"
            FIRECRAWL = f"{BASE}/firecrawl"

    class V0:  # Use lowercase for consistency with prefix
        """API routes (versioned)."""

        SOURCES = "/sources"
        CHAT = "/chat"
        CONVERSATIONS = "/conversations"

        class Sources:
            """Content management routes."""

            SOURCES = "/sources"
            SOURCE = "/sources/{source_id}"
            SOURCE_EVENTS = "/sources/{source_id}/events"
            SOURCE_STATUS = "/sources/{source_id}/status"

        class Chat:
            """Chat routes."""

            CHAT = "/chat"  # for sending and receiving messages

        class Conversations:
            """Conversation routes."""

            LIST = "/conversations"  # for getting conversation list
            GET = "/conversations/{conversation_id}"  # for getting a single conversation
