# 🚀 RAG 4 Docs - LLMs + up to date docs

## 🌟 Overview

RAG for Docs is a Retrieval-Augmented Generation (RAG) system designed to improve LLM responses when working with recent or private documentation. This project aims to reduce hallucinations and inaccuracies in LLM outputs by providing access to up-to-date information.

## ❓Why?
Large Language Models (LLMs) often lack access to the most recent documentation or private knowledge, leading to hallucinations in answers or inaccurate or outdated information in responses. This limits the usefulness of LLMs for buidling with the latest tools that were released after knowledge cutoff date.

What if LLMs could tap into a source of up to date information on libraries, tools, frameworks you are building with?

Imagine you could use the power of reasoning of modern LLMs but not be limited by their knowledgde cutoff date?

## 🎯 Goal
This project addresses these issues by implementing a RAG system that can access and utilize current documentation so that you can ask it to use any tool **in a correct way (without hallucinating or providing wrong implementation details**

## ⚙️ Key Features

- **🕷️ Intelligent Web Crawling**: Utilizes FireCrawl API to efficiently crawl and extract content from specified documentation websites.
- **🧠 Advanced Document Processing**: Implements custom chunking strategies to optimize document storage and retrieval.
- **🔍 Vector Search**: Employs Chroma DB for high-performance similarity search of document chunks.
- **🔄 Multi-Query Expansion**: Enhances search accuracy by generating multiple relevant queries for each user input.
- **📊 Smart Re-ranking**: Utilizes Cohere's re-ranking API to ensure the most relevant information is prioritized.
- **🤖 AI-Powered Responses**: Integrates with Claude 3.5 Sonnet to generate human-like, context-aware responses.

## 🛠️ Technical Stack

- **Language**: Python 3.7+
- **Web Crawling**: FireCrawl API
- **Vector Database**: Chroma DB
- **Embeddings**: OpenAI's text-embedding-3-small
- **LLM**: Anthropic's Claude 3.5 Sonnet
- **Re-ranking**: Cohere API
- **Additional Libraries**: tiktoken, chromadb, anthropic, cohere

## 🚀 Quick Start

1. **Clone the repository:**
   ```
   git clone https://github.com/Twist333d/rag-docs.git
   cd rag-docs
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root with the following:
   ```
   FIRECRAWL_API_KEY="your_firecrawl_api_key"
   OPENAI_API_KEY="your_openai_api_key"
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   COHERE_API_KEY="your_cohere_api_key"
   ```

3. **Install dependencies:**
   ```
   poetry install
   ```

4. **Run the application:**
   ```
   poetry run python app.py
   ```

## 💡 Usage

1. **Crawl Documentation:**
   To crawl documentation using FireCrawl you need to provide
   - base url - list of base urls to crawl
   - max_pages - the maximum number of pages that will be crawled
   - optional include/exclude tags - important in case you want precise control over the content

   ```python
   from src.crawling.crawler import FireCrawler

   crawler = FireCrawler(FIRECRAWL_API_KEY)
   urls_to_crawl = ["https://docs.yourlibrary.com"] # a list of base urls to crawl
   crawler.async_crawl_url(urls_to_crawl, page_limit=100)
   ```

2. **Chunk FireCrawl parsed docs:**
   Next step is to prepare chunks based on parsed markdown content from FireCrawl
   ```python
   from src.chunking.chunker import MarkdownChunker


   # Assuming your crawled file is named 'cra_docs_yourlibrary_com_20241026_123456.json'
   chunker = MarkdownChunker(input_filename="cra_docs_yourlibrary_com_20241026_123456.json")
   result = chunker.load_data()
   chunks = chunker.process_pages(result)
   chunker.save_chunks(chunks)
   ```

3. **Initialize application:**
   Finally, you can initialize the db, embed and store the downloaded documents and chat with them.
   ```python
    #
    file_names = [
        "your-crawled-and-chunked-docs-1.json",
        "your-crawled-and-chunked-docs-2.json",
        "your-crawled-and-chunked-docs-3.json",
    ]
    for file_name in file_names:
        document_loader = DocumentProcessor(file_name)
        json_data = document_loader.load_json()
        vector_db.add_documents(json_data, claude_assistant)
   ```

4. **Chat with documentation:**
   Don't forget to replace dummy filenames in the app.py with the files you've crawled to chat with them
   ```python
   python app.py
   ```

## ❤️‍🩹 Current Limitations
- Only terminal UI (no Chainlit for now)
- No automatic re-indexing of documents
- Basic chat flow supported
  - Either RAG tool is used or not
    - if a tool is used -> retrieves up to 5 most relevant documents (after re-ranking)

## 🛣️ Roadmap

- [ ] Implement user interface (chainlit)
- [ ] Allow user to save a URL / parse URL and sub-pages based on commands (a-ka Cursor style)
- [ ] Improve tool decision-making
- [ ] Streaming support
- [ ] Implement a basic search evaluation suite

## 📈 Performance Metrics
No eval suite is built yet (but will be added very soon)

- Average query processing time: [TBD]
- Retrieval accuracy (e.g., NDCG@5): [TBD]
- Response coherence (based on LLM evaluation): [TBD]


## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [FireCrawl](https://firecrawl.dev/) for superb web crawling
- [Chroma DB](https://www.trychroma.com/) for easy vector storage and retrieval
- [Anthropic](https://www.anthropic.com/) for Claude 3.5 Sonnet
- [OpenAI](https://openai.com/) for text embeddings
- [Cohere](https://cohere.ai/) for re-ranking capabilities

## 📞 Support

For any questions or issues, please [open an issue](https://github.com/yourusername/rag-4-docs/issues) or contact our support team at support@rag4docs.com.

---

Built with ❤️ by AZ
