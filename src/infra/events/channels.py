from uuid import UUID


class Channels:
    """Channel definitions for pub/sub events"""

    # Base namespaces
    SOURCES = "sources"
    CHAT = "chat"

    class Sources:
        """Sources-related channels"""

        @staticmethod
        def source_events_channel(source_id: UUID) -> str:
            "Channel for source SSE events."
            return f"{Channels.SOURCES}/{str(source_id)}/events"

        @staticmethod
        def processing_channel() -> str:
            "Channel for source processing events."
            return f"{Channels.SOURCES}/processing"

    class Config:
        """Configuration for channels"""

        SSE_TIMEOUT = 60 * 60  # 1 hour
