from uuid import UUID


class Channels:
    """Channel definitions for pub/sub events"""

    # Base namespaces
    CONTENT_PROCESSING = "content_processing"
    CHAT = "chat"

    @staticmethod
    def content_processing_channel(source_id: UUID | str) -> str:
        """Creates a source-specific content processing channel."""
        return f"{Channels.CONTENT_PROCESSING}/{str(source_id)}"

    class Config:
        """Configuration for channels"""

        SSE_TIMEOUT = 60 * 60  # 1 hour
