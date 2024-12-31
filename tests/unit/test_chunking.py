import pytest

from src.core.content.chunker import MarkdownChunker


@pytest.mark.unit
def test_markdown_chunker_initialization():
    """Test that MarkdownChunker initializes with correct settings."""
    chunker = MarkdownChunker()
    assert chunker.chunk_size == 512  # Updated to match current implementation
    assert chunker.chunk_overlap == 50
