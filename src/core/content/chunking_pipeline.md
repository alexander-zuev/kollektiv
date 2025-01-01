## Chunking Pipeline

Description of a high-level pipeline for how the chunking process works.

class MarkkdownChunker:
- Responsibilities:
    - Inputs: list[Document]
    - Outputs: list[Chunk]
    - Custom-built logic for chunking markdown.
    - Removes boilerplate, images from input documents before processing.
    - Ensures headers fallback to page title if missing.
    - Validates chunks after processing.
    - Batches documents and chunks into batches before processing.

- High-level logic:
    - Does page by page processing
    - For each page it extracts content and metadata
    - Content processing:
        - Removes boilerplate
        - Removes images
        - Identifies sections
        - Creates chunks
        - Ensures headers fallback to page title if missing
        - Validates chunks
    - Metadata processing:

- Edge cases:
    - Empty page content
    - Pages without headers
    - Pages with irregular structure - for example, only headers or headers of certain levels
    - Any other edge cases?
    - Code blocks?
    - Tables?
    - Lists?
    - What other markdown elements should be handled?

- Validation:
    - Validate headers are preserved per page?
    - Valiade median chunk token size?
    - Validate chunk overlap?
