# RAG Docs User Guide

RAG Docs is a powerful Retrieval-Augmented Generation (RAG) system that allows you to chat with up-to-date library documentation. This guide will walk you through the process of setting up, running, and using the RAG Docs system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Installation](#installation)
3. [Usage Scenarios](#usage-scenarios)
   - [First-Time Setup](#first-time-setup)
   - [Adding New Documentation](#adding-new-documentation)
   - [Chatting with Existing Documentation](#chatting-with-existing-documentation)
4. [Step-by-Step Guide](#step-by-step-guide)
   - [Crawling Documentation](#crawling-documentation)
   - [Chunking Documents](#chunking-documents)
   - [Embedding and Storing](#embedding-and-storing)
   - [Running the Chat Interface](#running-the-chat-interface)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

## System Overview

RAG Docs consists of several components that work together to provide an interactive chat experience with documentation:

1. Web Crawler: Uses the FireCrawl API to fetch documentation from specified websites.
2. Document Processor: Chunks the crawled documents into manageable pieces.
3. Vector Database: Stores document chunks and their embeddings for efficient retrieval.
4. Embedding Generator: Creates vector representations of document chunks.
5. Query Expander: Generates multiple relevant queries to improve search results.
6. Re-ranker: Improves the relevance of retrieved documents.
7. AI Assistant: Interacts with users and generates responses based on retrieved information.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rag-docs.git
cd rag-docs
```
2. Install dependencies:
```bash
poetry install
```
3. Set up environment variables:
Create a `.env` file in the project root with the following:
```bash
FIRECRAWL_API_KEY="your_firecrawl_api_key"
OPENAI_API_KEY="your_openai_api_key"
ANTHROPIC_API_KEY="your_anthropic_api_key"
COHERE_API_KEY="your_cohere_api_key"
```

## Usage Scenarios

### First-Time Setup

When using RAG Docs for the first time, you'll need to crawl documentation, process it, and set up the vector database. Follow these steps:

1. Crawl documentation (see [Crawling Documentation](#crawling-documentation))
2. Chunk the crawled documents (see [Chunking Documents](#chunking-documents))
3. Embed and store the chunks (see [Embedding and Storing](#embedding-and-storing))
4. Run the chat interface (see [Running the Chat Interface](#running-the-chat-interface))

### Adding New Documentation

To add new documentation to an existing RAG Docs setup:

1. Crawl the new documentation
2. Chunk the new documents
3. Embed and store the new chunks
4. Restart the chat interface to include the new information

### Chatting with Existing Documentation

If you've already set up RAG Docs with embedded documentation:

1. Run the chat interface
2. Start asking questions about the documentation

## Step-by-Step Guide

### Crawling Documentation

To crawl documentation using FireCrawl:

1. Open `crawler.py`
2. Modify the `urls_to_crawl` list with the URLs you want to crawl
3. Run the crawler:
```bash
python src/crawling/crawler.py
```

Example:
```python
urls_to_crawl = [
 "https://docs.yourlibrary.com",
 "https://api.anotherlibrary.com"
]
crawler.async_crawl_url(urls_to_crawl, page_limit=100)
```
This will save the crawled data in the src/data/raw directory.

### Chunking Documents

After crawling, you need to chunk the documents:

1. Open chunking.py
2. Update the input_filename with the name of your crawled file
3. Run the chunker:
```bash
python src/chunking/chunking.py
```
Example
```python
markdown_chunker = MarkdownChunker(input_filename="cra_docs_yourlibrary_com_20240526_123456.json")
result = markdown_chunker.load_data()
chunks = markdown_chunker.process_pages(result)
markdown_chunker.save_chunks(chunks)
```

This will save the chunked data in the src/data/chunks directory.

### Embedding and Storing

To embed and store the chunks:

1. Open `app.py`
2. Update the `file_names` list with your chunked document files
3. Run the embedding and storing process:
```bash
python app.py
```
Example
```python
file_names = [
    "cra_docs_yourlibrary_com_20240526_123456-chunked.json",
    "cra_docs_anotherlibrary_com_20240526_123457-chunked.json",
]
for file_name in file_names:
    document_loader = DocumentProcessor(file_name)
    json_data = document_loader.load_json()
    vector_db.add_documents(json_data, claude_assistant)
```
This will embed the chunks and store them in the vector database.

### Running the Chat Interface
To start chatting with the documentation:

1. Ensure all previous steps are completed
2. Run the main application:
```bash
python app.py
```
3. Start asking questions in the terminal interface

## Advanced Usage
### Customizing Chunking Parameters
You can customize the chunking process by modifying parameters in the MarkdownChunker class:
```python
markdown_chunker = MarkdownChunker(
    input_filename="your_file.json",
    max_tokens=1000,
    soft_token_limit=800,
    min_chunk_size=100,
    overlap_percentage=0.05
)
```
### Modifying the AI Assistant
To change the behavior of the AI assistant, you can update the system prompt in claude_assistant.py:
```python
self.base_system_prompt = """
    Your custom instructions here...
"""
```
## Troubleshooting

- **Crawling Issues:** Ensure your FireCrawl API key is correct and you have sufficient credits.
- **Chunking Errors:** Check the input JSON file format and ensure it matches the expected structure.
- **Embedding Failures:** Verify your OpenAI API key and check for rate limiting issues.
- **Chat Interface Not Responding:** Make sure all components are initialized correctly and the vector database is
  populated.

For any other issues, check the log files in the `logs` directory for detailed error messages.
***
This user guide provides a comprehensive overview of the RAG Docs system. For further assistance or to report issues,
open an issue on the project's GitHub repository.
