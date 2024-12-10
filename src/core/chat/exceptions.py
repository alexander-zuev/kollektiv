"""Exceptions for chat-related operations."""

from typing import Optional

from src.core._exceptions import (
    ConnectionError,
    LLMError,
    StreamingError,
    TokenLimitError,
)


class ChatError(LLMError):
    """Base exception for chat-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class ConversationError(ChatError):
    """Raised when conversation operations fail."""
    pass


class ClientDisconnectError(StreamingError):
    """Raised when the client disconnects during streaming."""
    pass
