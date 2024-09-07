# Implement chunking

## Feature scope
- Process the input JSON data from FireCrawl
- Break down each page into meaningful chunks
- Generate summaries for each chunk using Claude 3 Haiku
- Output a structured JSON file with chunked and summarized content
- Prepare the output for embedding generation

## Input structure
The input is a JSON file containing scraped data from Supabase documentation. Each entry represents a page and includes:

base_url
timestamp
data (array of page objects)

content (raw HTML)
markdown (Markdown version of the content)
metadata (title, description, URL, etc.)

```json
{
  "base_url": "https://supabase.com/docs/",
  "timestamp": "2024-08-30T07:30:45.664429",
  "data": [
    {
      "content": "[![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-dark.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-light.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)DOCS](/docs)\n\n*   [Start](/docs/guides/getting-started)\n    \n*   Products\n*   Build\n*   Reference\n*   Resources\n\n[![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-dark.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-light.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)DOCS](/docs)\n\nSearch docs...\n\nK\n\n### Where do I find support?\n\nChoose the support channel relevant for your situation here: [supabase.com/support](https://supabase.com/support)\n\n### How much does it cost?\n\nSelf-hosting Supabase is free. If you wish to use our cloud-platform, we provide [simple, predictable pricing](https://supabase.com/pricing)\n.\n\n### How do I host Supabase?\n\nYou can use the docker compose script [here](https://github.com/supabase/supabase/tree/master/docker)\n, and find detailed instructions [here](/docs/guides/hosting/overview)\n.\n\nSupabase is an amalgamation of open source tools. Some of these tools are made by Supabase (like our [Realtime Server](https://github.com/supabase/realtime)\n), some we support directly (like [PostgREST](http://postgrest.org/en/v7.0.0/)\n), and some are third-party tools (like [KonSupabase is an amalgamation open sourceg](https://github.com/Kong/kong)\n).\n\nAll of the tools we use in Supabase are MIT, Apache 2.0, or PostgreSQL licensed. This is one of the requirements to be considered for the Supabase stack.\n\n### How can you be a Firebase alternative if you're built with a relational database?\n\nWe started Supabase because we love the functionality of Firebase, but we personally experienced the scaling issues that many others experienced. We chose Postgres because it's well-trusted, with phenomenal scalability.\n\nOur goal is to make Postgres as easy to use as Firebase, so that you no longer have to choose between usability and scalability. We're sure that once you start using Postgres, you'll love it more than any other database.\n\n### Do you support `[some other database]`?\n\nWe only support PostgreSQL. It's unlikely we'll ever move away from Postgres; however, you can [vote on a new database](https://github.com/supabase/supabase/discussions/6)\n if you want us to start development.\n\n### Do you have a library for `[some other language]`?\n\nWe officially support [JavaScript](/docs/reference/javascript/installing)\n, [Swift](/docs/reference/swift/installing)\n, and [Flutter](/docs/reference/dart/installing)\n.\n\nYou can find community-supported libraries including Python, C#, PHP, and Ruby in our [GitHub Community](https://github.com/supabase-community)\n, and you can also help us to identify the most popular languages by [voting for a new client library](https://github.com/supabase/supabase/discussions/5)\n.\n\n*   Need some help?\n    \n    [Contact support](https://supabase.com/support)\n    \n*   Latest product updates?\n    \n    [See Changelog](https://supabase.com/changelog)\n    \n*   Something's not right?\n    \n    [Check system status](https://status.supabase.com/)\n    \n\n* * *\n\n[\u00a9 Supabase Inc](https://supabase.com/)\n\u2014[Contributing](https://github.com/supabase/supabase/blob/master/apps/docs/DEVELOPERS.md)\n[Author Styleguide](https://github.com/supabase/supabase/blob/master/apps/docs/CONTRIBUTING.md)\n[Open Source](https://supabase.com/open-source)\n[SupaSquad](https://supabase.com/supasquad)\nPrivacy Settings\n\n[GitHub](https://github.com/supabase/supabase)\n[Twitter](https://twitter.com/supabase)\n[Discord](https://discord.supabase.com/)",
      "markdown": "[![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-dark.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-light.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)DOCS](/docs)\n\n*   [Start](/docs/guides/getting-started)\n    \n*   Products\n*   Build\n*   Reference\n*   Resources\n\n[![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-dark.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)![Supabase wordmark](https://supabase.com/docs/_next/image?url=%2Fdocs%2Fsupabase-light.svg&w=256&q=75&dpl=dpl_FamQvESN35BiTrVL2ZnRKQ5butin)DOCS](/docs)\n\nSearch docs...\n\nK\n\n### Where do I find support?\n\nChoose the support channel relevant for your situation here: [supabase.com/support](https://supabase.com/support)\n\n### How much does it cost?\n\nSelf-hosting Supabase is free. If you wish to use our cloud-platform, we provide [simple, predictable pricing](https://supabase.com/pricing)\n.\n\n### How do I host Supabase?\n\nYou can use the docker compose script [here](https://github.com/supabase/supabase/tree/master/docker)\n, and find detailed instructions [here](/docs/guides/hosting/overview)\n.\n\nSupabase is an amalgamation of open source tools. Some of these tools are made by Supabase (like our [Realtime Server](https://github.com/supabase/realtime)\n), some we support directly (like [PostgREST](http://postgrest.org/en/v7.0.0/)\n), and some are third-party tools (like [KonSupabase is an amalgamation open sourceg](https://github.com/Kong/kong)\n).\n\nAll of the tools we use in Supabase are MIT, Apache 2.0, or PostgreSQL licensed. This is one of the requirements to be considered for the Supabase stack.\n\n### How can you be a Firebase alternative if you're built with a relational database?\n\nWe started Supabase because we love the functionality of Firebase, but we personally experienced the scaling issues that many others experienced. We chose Postgres because it's well-trusted, with phenomenal scalability.\n\nOur goal is to make Postgres as easy to use as Firebase, so that you no longer have to choose between usability and scalability. We're sure that once you start using Postgres, you'll love it more than any other database.\n\n### Do you support `[some other database]`?\n\nWe only support PostgreSQL. It's unlikely we'll ever move away from Postgres; however, you can [vote on a new database](https://github.com/supabase/supabase/discussions/6)\n if you want us to start development.\n\n### Do you have a library for `[some other language]`?\n\nWe officially support [JavaScript](/docs/reference/javascript/installing)\n, [Swift](/docs/reference/swift/installing)\n, and [Flutter](/docs/reference/dart/installing)\n.\n\nYou can find community-supported libraries including Python, C#, PHP, and Ruby in our [GitHub Community](https://github.com/supabase-community)\n, and you can also help us to identify the most popular languages by [voting for a new client library](https://github.com/supabase/supabase/discussions/5)\n.\n\n*   Need some help?\n    \n    [Contact support](https://supabase.com/support)\n    \n*   Latest product updates?\n    \n    [See Changelog](https://supabase.com/changelog)\n    \n*   Something's not right?\n    \n    [Check system status](https://status.supabase.com/)\n    \n\n* * *\n\n[\u00a9 Supabase Inc](https://supabase.com/)\n\u2014[Contributing](https://github.com/supabase/supabase/blob/master/apps/docs/DEVELOPERS.md)\n[Author Styleguide](https://github.com/supabase/supabase/blob/master/apps/docs/CONTRIBUTING.md)\n[Open Source](https://supabase.com/open-source)\n[SupaSquad](https://supabase.com/supasquad)\nPrivacy Settings\n\n[GitHub](https://github.com/supabase/supabase)\n[Twitter](https://twitter.com/supabase)\n[Discord](https://discord.supabase.com/)",
      "metadata": {
        "title": "Supabase Docs",
        "language": "en",
        "sourceURL": "https://supabase.com/docs/faq",
        "pageStatusCode": 200,
        "ogLocaleAlternate": []
      },
      "linksOnPage": [
        "https://supabase.com/docs",
        "https://supabase.com/docs/guides/getting-started",
        "https://supabase.com/support",
        "https://supabase.com/pricing",
        "https://github.com/supabase/supabase/tree/master/docker",
        "https://supabase.com/docs/guides/hosting/overview",
        "https://github.com/supabase/realtime",
        "http://postgrest.org/en/v7.0.0/",
        "https://github.com/Kong/kong",
        "https://github.com/supabase/supabase/discussions/6",
        "https://supabase.com/docs/reference/javascript/installing",
        "https://supabase.com/docs/reference/swift/installing",
        "https://supabase.com/docs/reference/dart/installing",
        "https://github.com/supabase-community",
        "https://github.com/supabase/supabase/discussions/5",
        "https://supabase.com/changelog",
        "https://status.supabase.com/",
        "https://supabase.com/",
        "https://github.com/supabase/supabase/blob/master/apps/docs/DEVELOPERS.md",
        "https://github.com/supabase/supabase/blob/master/apps/docs/CONTRIBUTING.md",
        "https://supabase.com/open-source",
        "https://supabase.com/supasquad",
        "https://github.com/supabase/supabase",
        "https://twitter.com/supabase",
        "https://discord.supabase.com/"
      ]
    },
```

## Example RAG from Anthropic RAG tutorial
URL: https://github.com/anthropics/anthropic-cookbook/blob/main/skills/retrieval_augmented_generation/guide.ipynb

### Chunk structure
This is the structure of the docs they used in Anthropic tutorial on RAG.
```json
[
  {
    "chunk_link": "https://docs.anthropic.com/en/docs/welcome#get-started",
    "chunk_heading": "Get started",
    "text": "Get started\n\n\nIf you\u2019re new to Claude, start here to learn the essentials and make your first API call.\nIntro to ClaudeExplore Claude\u2019s capabilities and development flow.QuickstartLearn how to make your first API call in minutes.Prompt LibraryExplore example prompts for inspiration.\nIntro to ClaudeExplore Claude\u2019s capabilities and development flow.\n\nIntro to Claude\nExplore Claude\u2019s capabilities and development flow.\nQuickstartLearn how to make your first API call in minutes.\n\nQuickstart\nLearn how to make your first API call in minutes.\nPrompt LibraryExplore example prompts for inspiration.\n\nPrompt Library\nExplore example prompts for inspiration.\n"
  },
  {
    "chunk_link": "https://docs.anthropic.com/en/docs/welcome#models",
    "chunk_heading": "Models",
    "text": "Models\n\n\nClaude consists of a family of large language models that enable you to balance intelligence, speed, and cost.\n\n\n\n\n\nCompare our state-of-the-art models.\n"
  },
  {
    "chunk_link": "https://docs.anthropic.com/en/docs/welcome#develop-with-claude",
    "chunk_heading": "Develop with Claude",
    "text": "Develop with Claude\n\n\nAnthropic has best-in-class developer tools to build scalable applications with Claude.\nDeveloper ConsoleEnjoy easier, more powerful prompting in your browser with the Workbench and prompt generator tool.API ReferenceExplore, implement, and scale with the Anthropic API and SDKs.Anthropic CookbookLearn with interactive Jupyter notebooks that demonstrate uploading PDFs, embeddings, and more.\nDeveloper ConsoleEnjoy easier, more powerful prompting in your browser with the Workbench and prompt generator tool.\n\nDeveloper Console\nEnjoy easier, more powerful prompting in your browser with the Workbench and prompt generator tool.\nAPI ReferenceExplore, implement, and scale with the Anthropic API and SDKs.\n\nAPI Reference\nExplore, implement, and scale with the Anthropic API and SDKs.\nAnthropic CookbookLearn with interactive Jupyter notebooks that demonstrate uploading PDFs, embeddings, and more.\n\nAnthropic Cookbook\nLearn with interactive Jupyter notebooks that demonstrate uploading PDFs, embeddings, and more.\n"
  },
  {
    "chunk_link": "https://docs.anthropic.com/en/docs/welcome#key-capabilities",
    "chunk_heading": "Key capabilities",
    "text": "Key capabilities\n\n\nClaude can assist with many tasks that involve text, code, and images.\nText and code generationSummarize text, answer questions, extract data, translate text, and explain and generate code.VisionProcess and analyze visual input and generate text and code from images.\nText and code generationSummarize text, answer questions, extract data, translate text, and explain and generate code.\n\nText and code generation\nSummarize text, answer questions, extract data, translate text, and explain and generate code.\nVisionProcess and analyze visual input and generate text and code from images.\n\nVision\nProcess and analyze visual input and generate text and code from images.\n"
  },
  {
    "chunk_link": "https://docs.anthropic.com/en/docs/welcome#support",
    "chunk_heading": "Support",
    "text": "Support\n\n\nHelp CenterFind answers to frequently asked account and billing questions.Service StatusCheck the status of Anthropic services.\nHelp CenterFind answers to frequently asked account and billing questions.\n\nHelp Center\nFind answers to frequently asked account and billing questions.\nService StatusCheck the status of Anthropic services.\n\nService Status\nCheck the status of Anthropic services.\nQuickstartxlinkedin\nQuickstart\nxlinkedin\nGet started Models Develop with Claude Key capabilities Support\nGet startedModelsDevelop with ClaudeKey capabilitiesSupport\n"
  },
```

So each chunk has:
- chunk_link -> seems like they broke it by sections.
- chunk_heading -> which seems to be the section name.
- text: text of the chunk

### Embedding approach
```python
def load_data(self, data):
        if self.embeddings and self.metadata:
            print("Vector database is already loaded. Skipping data loading.")
            return
        if os.path.exists(self.db_path):
            print("Loading vector database from disk.")
            self.load_db()
            return

        texts = [f"Heading: {item['chunk_heading']}\n\n Chunk Text:{item['text']}" for item in data]
        self._embed_and_store(texts, data)
        self.save_db()
        print("Vector database loaded and saved.")
```

So how did they create each chunk for embeddings:
- they created a list where each chunk had it's heading + text
- then they passed it into the embedding model
- later they added summary of the heading + text and appending 'summary' to the chunk

Final chunk structure is:
```python
summarized_doc = {
    "chunk_link": doc["chunk_link"],
    "chunk_heading": doc["chunk_heading"],
    "text": doc["text"],
    "summary": summary
}
```

Summary was generated by the model using this approach:
```python
def generate_summaries(input_file, output_file):
 
    # Load the original documents
    with open(input_file, 'r') as f:
        docs = json.load(f)

    # Prepare the context about the overall knowledge base
    knowledge_base_context = "This is documentation for Anthropic's, a frontier AI lab building Claude, an LLM that excels at a variety of general purpose tasks. These docs contain model details and documentation on Anthropic's APIs."

    summarized_docs = []

    for doc in tqdm(docs, desc="Generating summaries"):
        prompt = f"""
        You are tasked with creating a short summary of the following content from Anthropic's documentation. 

        Context about the knowledge base:
        {knowledge_base_context}

        Content to summarize:
        Heading: {doc['chunk_heading']}
        {doc['text']}

        Please provide a brief summary of the above content in 2-3 sentences. The summary should capture the key points and be concise. We will be using it as a key part of our search pipeline when answering user queries about this content. 

        Avoid using any preamble whatsoever in your response. Statements such as 'here is the summary' or 'the summary is as follows' are prohibited. You should get straight into the summary itself and be concise. Every word matters.
        """

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        summary = response.content[0].text.strip()

        summarized_doc = {
            "chunk_link": doc["chunk_link"],
            "chunk_heading": doc["chunk_heading"],
            "text": doc["text"],
            "summary": summary
        }
        summarized_docs.append(summarized_doc)

    # Save the summarized documents to a new JSON file
    with open(output_file, 'w') as f:
        json.dump(summarized_docs, f, indent=2)

    print(f"Summaries generated and saved to {output_file}")

# generate_summaries('data/anthropic_docs.json', 'data/anthropic_summary_indexed_docs.json')
```
Summary increased the key metrics of RAG by either small or medium amount (specifically recall increased from 0.56 
to 0.71)

# Chunking and Processing Approach for Supabase Documentation

## 0. Markdown content structure analysis
- consistent heading markers:
  - h1 #
  - h2 ##
  - h3 ###
- Code blocks defined by triple ticks
- Lists
- Links
- Horizontal rules

## 1. Step-by-Step Processing Approach

1. Load JSON data from FireCrawl
2. Extract and parse markdown content for each page
4. Generate chunks based on heading hierarchy and content
5. Calculate token counts using tiktoken
6. Generate summaries using Google Gemini 1.5 Flash (batch mode)
7. Validate chunks and generate report
8. Save processed chunks and validation report

## 2. Target Chunk Structure

```json
{
      "source_url": "https://supabase.com/docs/reference/python/initializing",
      "headers": {
        "H1": ""
      },
      "content": "\nPython Client Library=====================\n\nsupabase-py[View on GitHub](https://github.com/supabase/supabase-py)\n\nThis reference documents every object and method available in Supabase's Python library, [supabase-py](https://github.com/supabase/supabase-py)\n. You can use supabase-py to interact with your Postgres database, listen to database changes, invoke Deno Edge Functions, build login and user management functionality, and manage large files.\n\n* * *\n",
      "chunk_id": "c6b5fde8-d48b-43e8-a77f-04035d1a61f7",
      "token_count": 113,
      "has_code_block": false
    },
```

## 3. Updated End-to-End Approach

### Input Processing (DONE & TESTED)
- Load JSON data from FireCrawl
- Implement error handling for malformed JSON or missing required fields

### Document Parsing and Chunking  (DONE & TESTED)
- Utilize the markdown library to convert Markdown to HTML for easier line-by-line processing.
- Implement line-by-line parsing logic as described in Section 2.
- Generate and manage chunks based on heading hierarchy and token limits.
- Handle code blocks as single units, flagging oversized ones. (SKIPPED)

### Summarization (SKIPPED)
- Generate summaries for each chunk using Google Gemini 1.5 Flash
- Implement batch processing for API calls
- Use a rate limiter to avoid exceeding API limits
- Implement retry logic for failed API calls

### Validation and Reporting
- Check for lost H1 and H2 headings
- Perform smart token count validation
- Generate and display summary statistics

### Output Generation
- Structure chunks and summaries into JSON format
- Save output file

## 4. Components, Functions, and Methods

### InputProcessor
- `load_json(file_path: str) -> Dict`
- `validate_input(data: Dict) -> bool`

### Chunker
- `parse_markdown(content: str, source_url: str) -> List[Dict[str, Any]]`
- `create_chunk(source_url: str) -> Dict[str, Any]`
- `calculate_token_count(text: str) -> int`

### Summarizer
- `batch_summarize(chunks: List[EnrichedChunk]) -> List[str]`
- `retry_api_call(func: Callable, max_retries: int, backoff_factor: float) -> Any`

### Validator
- `validate_headings_preserved(original_doc: str, chunks: List[EnrichedChunk]) -> bool`
- `validate_token_counts(original_doc: str, chunks: List[EnrichedChunk]) -> bool`
- `generate_validation_report(original_doc: str, chunks: List[EnrichedChunk]) -> Dict`

### StatisticsGenerator
- `generate_statistics(original_docs: List[str], chunks: List[EnrichedChunk]) -> Dict`

### Orchestrator
- `run(input_file: str, output_file: str)`
- `process_document(doc: Dict) -> List[EnrichedChunk]`
- `summarize_chunks(chunks: List[EnrichedChunk]) -> List[str]`
- `validate_and_report(original_doc: str, chunks: List[EnrichedChunk])`

## 5. Scalability Considerations

- Implement comprehensive multiprocessing for CPU-bound tasks
- Use async/await for I/O-bound operations (e.g., API calls for summarization)
- Use generators for memory-efficient processing of large datasets
- Implement progress bars and summary statistics for user feedback
- Use batch processing for large datasets that don't fit in memory

### Multiprocessing Implementation
Use Python's `multiprocessing` module to parallelize CPU-bound tasks. The `Orchestrator` class will manage the distribution of work across available CPU cores.

### Asynchronous Summarization
Implement asynchronous processing for batch API calls to Google Gemini 1.5 Flash for summary generation. This allows for concurrent API calls, significantly reducing the overall time for summarization.

## 6. CLI Approach for Main Orchestrator
Implement a command-line interface for the main orchestrator, allowing users to specify input and output files, as well as optional parameters like maximum tokens per chunk and summary length.

## 7. Validator Integration with Orchestrator
The validator is integrated directly into the Orchestrator's workflow. It performs checks after processing each document and provides a detailed report to the user.

## 8. Summary Generator Output
The StatisticsGenerator provides comprehensive statistics about the chunking process, including:

- Original document count and token count
- Unique URLs processed
- Total chunks generated
- Token count statistics (total, average, min, max)
- Heading counts (H1, H2)
- Number of chunks with code blocks
- Identified issues (e.g., chunks outside the desired token range)

## 9. Progress Tracking and User Feedback
Implement progress bars using the `tqdm` library to provide real-time feedback on:

- Document processing progress
- Summary generation progress

Display summary statistics and validation results at the end of the process.

## 10. Error Handling and Logging
Implement comprehensive error handling and logging throughout the pipeline to catch and report any issues during processing.

## 11. Extensibility
Design the system with extensibility in mind, allowing for easy addition of new features or modifications to existing components without major refactoring.

## 12. Handling Edge Cases and Varying Document Structures

### Inconsistent Heading Hierarchy:
- If a document doesn't start with an H1, use the document title or first heading as H1
- If H2 appears before H1, treat it as an H1 until a true H1 is encountered
- Handle missing intermediate levels (e.g., H1 followed directly by H3)

### No Clear Headings:
- For documents with no clear heading structure, create chunks based on paragraph breaks or a maximum token count
- Use the document title or first sentence as the H1 for all chunks

### Very Short Documents:
- If a document is shorter than the minimum chunk size, keep it as a single chunk
- Add a note in the metadata indicating it's a full document

### Very Long Sections:
- If content between headings exceeds the maximum chunk size, split it into multiple chunks
- Maintain the same heading information for all resulting chunks, but add a part number (e.g., "Part 1", "Part 2")

### Code Blocks:
- Never split within a code block
- If a code block exceeds the maximum chunk size, keep it as a single oversized chunk and flag it in the metadata