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
**Context View**
- As a user, I want the chunking to work in 1 click by breaking down the parsed documents for me
- As a user, I want to be able to download Supabase docs, validate them and use them for working with data

**Logical view**
### Crawling
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
- cancel_job(job_id):
  - cancels a given job
- retrieve_job_results(job_id)
  - retrieves job results by id
- save_raw_data(job_results, raw_data_path):
  - saves job results in the raw_data_dir
- summarize_data(file_path):
  - summarize the main attributes of the parsed docs:
    - number of pages
    - number of unique URLS

### Chunking

**Process View**
- https://www.figma.com/board/wtYU0jzyG2U1N5vdmEoqag/RAG4Docs?node-id=0-1&t=Y63pZ8PnKT6DKF4E-1

## Open questions

## Implementation details

## Evaulation