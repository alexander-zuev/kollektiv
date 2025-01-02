## Chunking Pipeline

Description of a high-level pipeline for how the chunking process works.

### class MarkdownChunker
- Responsibilities:
  - Inputs: list[Document]
  - Outputs: list[Chunk]
  - Performs custom logic for chunking markdown, including:
    - Removing boilerplate and images from input documents
    - Ensuring headers fallback to page title if missing
    - Validating chunks post-processing
    - Batching documents and chunks before processing

### Key Parameters

1. **max_tokens (hard limit)**  
   - The absolute maximum number of tokens in any single chunk.  
   - Proposed default: 512.  
   - Ensures each chunk stays within typical LLM context boundaries.

2. **soft_token_limit**  
   - A “target” chunk size—if new content stays below this limit, it goes into the current chunk.  
   - Proposed default: ~450 tokens.   
   - Helps create chunks that are large enough for context, yet comfortably within the hard limit.

3. **min_chunk_size**  
   - The minimum size for a chunk in tokens before attempting to merge it with a neighbor.  
   - Proposed default: ~100 tokens.  
   - Avoids huge numbers of tiny fragments.

4. **overlap_percentage**  
   - How much overlap to add from the end of one chunk to the beginning of the next for better context.  
   - Proposed default: 5%.  
   - Capped to avoid runaway chunk size.

5. **document_batch_size**  
   - Number of Documents processed at a time in Celery.  
   - Proposed default: 50.  
   - Prevents memory overload and improves parallelism.

6. **chunk_batch_size**  
   - Number of Chunks grouped before being passed for embedding or storage.  
   - Proposed default: 500.  
   - Keeps embedding requests or DB saves at manageable sizes.

### High-Level Logic

1. **Page-by-Page Processing**  
   - The chunker processes documents page by page.  
   - Each page’s content is cleaned, split by headers, and chunked.

2. **Preprocessing**  
   - Remove boilerplate text via regex (see below).  
   - Strip out images (HTML tags, markdown image syntax, base64).  
   - Normalize extra blank lines and replace them with minimal spacing.

   **Boilerplate Removal:**  
   - We specifically remove or skip lines like:  
     - “Navigation,” “Search…,” “Copyright,” “All rights reserved,”  
     - automatically generated table-of-contents lines (like “On this page”),  
     - repeated headings that appear on every page (e.g., “English,” “Ctrl K”).  
   - Rationale: This text adds no real value to the content and would clutter our vector search index.

3. **Identify Sections**  
   - Split by markdown headers like #, ##, ###.  
   - Track code blocks (``` or ~~~) so they stay together.  
   - Accumulate lines until we approach the soft_token_limit or see a new section header.

4. **Create Chunks**  
   - Once we near soft_token_limit (512 tokens), finalize the current chunk.  
   - If an individual block alone exceeds max_tokens (512 tokens), we may further split it (especially for large code blocks).  
   - If a chunk is under min_chunk_size (~100 tokens), attempt to merge it with adjacent chunks.

5. **Apply Overlap**  
   - Optionally copy the last few tokens (≈5% of the chunk) of the previous chunk to the start of the next chunk.  
   - Improves context continuity for retrieval-augmented generation.

6. **Validation**  
   - Check for unclosed code blocks.  
   - Ensure no chunk surpasses max_tokens (512).  
   - Warn if chunk creation fails or leads to unexpected results.

7. **Batching**  
   - Documents are processed in sets of (e.g.) 50.  
   - Chunks are further batched (e.g., 500) prior to embedding or database insertion.

### Edge Cases

1. **Empty Page Content**  
   - Skip entirely or log a warning; no chunks produced.  

2. **Pages Without Headers**  
   - Treat everything as one section, fallback to using page title as an H1 if present.  

3. **Only h2+ or h3 Headers**  
   - If there is no h1 but we have h2 or h3, treat them as the top-level headers, preserving their structure.  
   - If a page has only h3, keep them under an implied empty h1/h2.  

4. **Only h1 Headers**  
   - If no subheadings exist, the chunker just accumulates everything under a single H1 section until the chunk size limit is reached.  

5. **Irregular Markdown Structure**  
   - If the file has only headers (no content lines), we still form minimal chunks containing the headers themselves.  
   - If the file has large blocks (e.g., big code samples), we split them by line or code fences once they exceed the max token limit.

6. **Code Blocks**  
   - If a code block itself exceeds 2×max_tokens, split it logically at line breaks.  
   - Log a warning that code block was abnormally large.

7. **Tables, Lists, Other Markdown**  
   - No special handling by default; treat these entities as regular text.  
   - If needed, we can add splits for bullet points or table rows in the future.

### Post-Processing
1. **Final Cleanup**  
   - After merging/splitting, we can do a final pass to trim whitespace or rename leftover “Untitled” headings if the page has since acquired a valid heading.  
   - Optionally run a quick redundancy check to see if some chunks are duplicates or empty after merges.

2. **Metadata Enrichment**  
   - We may append additional metadata (e.g., user-provided tags, source domain) to each chunk if desired.

### Validation

1. **Header Preservation**  
   - If a page has headers, ensure the chunk includes them in a “headers” dict (h1, h2, h3), even if h1 is empty due to only h2 or h3 in the doc.

2. **Chunk Size Constraints**  
   - Each chunk must stay below max_tokens=512.  
   - The chunker aims for ~512 tokens where practical.

3. **Overlap Checks**  
   - Confirm overlap doesn’t push the chunk over max_tokens.  
   - If it does, skip adding overlap or log a warning.

4. **Handling Partial Headings**  
   - If the doc only has h2 or h3, we capture them as the top headings.  
   - Log a warning or note if the structure is truly unusual (like h4+ only, which might not appear in your typical pipeline logic).

5. **Error Logging**  
   - If a code block is unclosed or a chunk can’t be split, record an error or skip the problematic content.  
   - Possibly keep a “validation errors” list for each page.

### Process Flow

1. **Take a List of Documents**  
2. **Batch Them** (default 50 documents per task call)  
3. **For Each Document:**  
   - Preprocess the page(s) (remove boilerplate/images).  
   - Split into sections (by headers or code fences).  
   - Split or merge sections into token-sized chunks.  
   - Apply overlap if desired.  
   - Validate results.  
4. **Return List of Chunks**  
5. **Further Batch the Chunks** (e.g., 500) for embedding/storage steps.
