"""System prompt management for chat functionality."""
from typing import List, Optional


class SystemPrompt:
    """Manages system prompts for chat interactions."""

    def __init__(self, base_prompt: str):
        """Initialize system prompt.

        Args:
            base_prompt: Base system prompt text.
        """
        self.base_prompt = base_prompt
        self.document_summaries: List[str] = []

    def add_document_summary(self, summary: str) -> None:
        """Add a document summary to the system prompt.

        Args:
            summary: Document summary to add.
        """
        self.document_summaries.append(summary)

    def clear_document_summaries(self) -> None:
        """Clear all document summaries."""
        self.document_summaries = []

    def get_full_prompt(self) -> str:
        """Get the full system prompt including document summaries.

        Returns:
            Complete system prompt text.
        """
        if not self.document_summaries:
            return self.base_prompt

        summaries_text = "\n\nRelevant context:\n" + "\n".join(
            f"- {summary}" for summary in self.document_summaries
        )
        return f"{self.base_prompt}{summaries_text}"

    def to_anthropic(self) -> str:
        """Convert system prompt to Anthropic API format."""
        return self.get_full_prompt()

    @property
    def has_document_context(self) -> bool:
        """Check if document summaries are present.

        Returns:
            True if document summaries exist, False otherwise.
        """
        return len(self.document_summaries) > 0
