from src.core.content.chunker import MarkdownChunker


def test_markdown_chunker_initialization():
    """
    Test the initialization of the MarkdownChunker class.

    Asserts:
        - The chunker instance is not None.
        - The max_tokens attribute is set to 1000.
        - The soft_token_limit attribute is set to 800.

    Raises:
        AssertionError: If any of the assertions fail.
    """
    chunker = MarkdownChunker()
    assert chunker is not None
    assert chunker.max_tokens == 1000
    assert chunker.soft_token_limit == 800
