from src.processing.chunking import MarkdownChunker


def test_markdown_chunker_initialization():
    chunker = MarkdownChunker(input_filename="test_input.json")
    assert chunker is not None
    assert chunker.max_tokens == 1000
    assert chunker.soft_token_limit == 800
