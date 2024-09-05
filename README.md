# 🌟 RAG 4 Docs - Chat with (any) documentation

## Overview
This project implements a Retrieval-Augmented Generation (RAG) system for improving LLM responses with external knowledge.

## Features
- Document Ingestion: Crawl and store web content using FireCrawl API
- Vector Database: Store and retrieve document chunks and embeddings using Chroma DB
- Query Processing: Handle query processing and relevance determination
- LLM Integration: Interact with Claude 3 Sonnet for generating responses

## Setup
1. Install dependencies:
    ```
    poetry install
    ```
   
2. Set up environment variables:
- Create a `.env` file in the project root
- Add the following variables:
  ```
  FIRECRAWL_API_KEY="api_key"
  OPENAI_API_KEY="api_key"
  ANTHROPIC_API_KEY="api_key"
  GOOGLE_API_KEY="your_google_api_key"
  COHERE_API_KEY="api_key"
  ```

## Usage
(To be implemented)

## Testing
Run tests using pytest:
    ```python
    pytest tests/

## Acknowledgements
- FireCrawl
- ChromaDB
- Anthropic

## License
(Add license information)
