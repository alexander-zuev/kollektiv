import pytest

from src.core.content.chunker import MarkdownChunker


@pytest.mark.unit
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


@pytest.mark.unit
def test_remove_boilerplate():
    """
    Test the removal of boilerplate content from markdown text.

    Tests the removal of navigation elements, search boxes, and other common
    boilerplate patterns while preserving actual content.

    Asserts:
        - Common boilerplate patterns are removed
        - Actual content is preserved
        - Extra newlines are cleaned up

    Raises:
        AssertionError: If the boilerplate removal doesn't work as expected
    """
    chunker = MarkdownChunker()
    test_content = """
[Anthropic home page](/home)
English
Search...
Ctrl K
Navigation
* * *
# Real Content Heading
This is actual content that should be preserved.
On this page
* * *
More real content here.
    """

    expected_content = """# Real Content Heading
This is actual content that should be preserved.
More real content here."""

    cleaned_content = chunker.remove_boilerplate(test_content)
    assert cleaned_content.strip() == expected_content.strip()
