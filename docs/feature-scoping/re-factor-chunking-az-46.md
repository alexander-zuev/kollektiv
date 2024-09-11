# Description
Currently, chunking is very brittle and frankly incorrect. I need to re-factor the way chunking works so that a 
correct input is always provided as chunks into the vector database.

## Problem statements
- Chunks are not unique -> a sample query (How to upsert data) return 5 chunks with different ids, but the same text.
- Chunks are not structured properly with some missplacement of the content

## Scope
- Re-factor chunking strategy, while preserving the json structure (it's OK for now)
- Re-factor scraping to use FireCrawl API V1
- Add simple validation of chunks for:
  - uniqueness of content (no duplicate chunks)
  - before & after token count
  - completeness of all H1 headers and H2 headers

### Out of scope
- Flexible or smart chunking - that selects the chunking strategy based on the markdown structure. If it can be done 
  easily - then yes, but I doubt that. The MVP version should be limited to working with Supabase documentation only.

## Approach
### Context View**
- As a user, I want the chunking to work in 1 click by breaking down the parsed documents for me
- As a user, I want to be able to download Supabase docs, validate them and use them for working with data

### Logical view
**Crawling**
class FireCrawler:
attributes: (DONE)
- api_key: str
- app: class
- current_job_id: uuid
- interrupt_received: bool
- raw_data_dir: str
methods:
- crawl_url(url, include_paths, exclude_paths)
  - crawls the urls with given params
  - returns the json file in the data path
  - saves the job_id
- save_job_id(job_id):
  - saves the job id with necessary data for later retrieval
- retrieve_job_results(job_id)
  - retrieves job results by id
- save_raw_data(job_results, raw_data_path):
  - saves job results in the raw_data_dir

**Chunking**
- What is the content structure of markdown files?
  - Main header denoted with # 
  - Then there are multiple sections with ## headers
  - Some sections have ### sub-headers
  - Code blocks are enclosed in backticks (`)
  - There are horizontal rules (---) denoted end of the page (we don't need it, because we can rely on the items in 
    object list)
- What should be the chunking strategy:
  - Page-level chunking
    - Each chunk will contain information only from one page
  - Section-level chunking
    - Break down each page into sections based on H2 headers
  - Content capture
    - Between H1 and first H2:
      - If there is content -> make it a separate chunk
      - If there's no content -> skip creating chunk for this section (because headers would be captured as metadata)
    - Between H2 headers
      - Create a chunk for each H2 section, including any H3 subsections within it
    - Code block handling
      - Always keep code blocks intact. Neversplit in the middle of a code block
      - if a code block causes a chunk to exceed the token limit, make the code block it's own chunk
    - Token limits:
      - Hard limit: 1000 tokens
      - Soft limit: 800 tokens (20% below)
    - Chunk overlap
      - 5% of content of the previous chunk -> last sentence + last header
    - Metadata retention:
      - sourceUrl
      - page title
      - position in doc hierarchy
    - Handling long sections
      - If a section is too long -> split it into multiple chunks.
      - Split at paragraph boundaries or list item boundaries
    - Minimum chunk size
      - 100 tokens - but how to enforce this?
    - Header stacking
      - If multiple headers appear without content -> group them into single chunk
    - Implementation
      - First pass -> split into H1 an H2 sections
      - Second pass -> process each major section, splitting into chunks based on token count + content structure
      - Third pass -> adjust chunk boundaries to ensure code blocks are preserved and min/max token counts are respected
  - Class structure:
    - MarkdownChunker:
      - attributes
        - output_dir: str
      - methods:
        - load_date -> loads json
        - save_chunks -> saves processed chunks in an async, multi-processed manner
        - process_page -> loads a single page and does all the processing
        - identify_sections -> identifies all sections within the doc
        - create_chunks -> goes through each section and creates chunks
        - code_blocks -> identifies code blocks
  - Target chunk structure:

```json
{
  'chunk_id': uuid,
  'metadata': {
    'token_count': int,
    'sourceUrl': HttpUrl # from firecrawl,
    'page_title': str # from firecrawl,
  },
  'data': {
    'headers': {
      'h1': 'text',
      'h2': 'text'
    },
    'text': str,
    'overlap_text': {
      "prev_chunk_id": uuid of the previous chunk,
      'text' : 5% or (50-100 tokens) of text
    }
  }
}
```
- LlamaIndex results 
  - The chunks are much smaller than our target of 1000 tokens (soft limit 800).
  - Many chunks contain only headers or very short snippets of content.
  - The chunking doesn't seem to respect the hierarchical structure of the markdown (H1, H2, H3).
  - Code blocks appear to be split across multiple chunks.
  - There's no visible overlap between chunks.
- Great chunking resources
  - https://unstructured.io/blog/chunking-for-rag-best-practices
- I need to employ some kind of content-aware chunking strategy
  - LangChain and LlamaIndex are not suitable because their chunkers are not customizeble enough


**Process View**
- https://www.figma.com/board/wtYU0jzyG2U1N5vdmEoqag/RAG4Docs?node-id=0-1&t=Y63pZ8PnKT6DKF4E-1

## Open questions

## Implementation details

## Evaulation