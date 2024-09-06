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
- **Additional Libraries**: tiktoken, numpy, aiohttp

## 🚀 Quick Start

1. **Clone the repository:**
   \```
   git clone https://github.com/yourusername/rag-4-docs.git
   cd rag-4-docs
   \```

2. **Set up environment variables:**
   Create a `.env` file in the project root with the following:
   \```
   FIRECRAWL_API_KEY="your_firecrawl_api_key"
   OPENAI_API_KEY="your_openai_api_key"
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   COHERE_API_KEY="your_cohere_api_key"
   \```

3. **Install dependencies:**
   \```
   poetry install
   \```

4. **Run the application:**
   \```
   python main.py
   \```

## 💡 Usage

1. **Crawl Documentation:**
   \```python
   from src.input_processing.scraping import scrape_and_save

   base_url = "https://docs.yourlibrary.com"
   result_file = scrape_and_save(base_url, max_pages=100)
   \```

2. **Process Documents:**
   \```python
   from src.document_ingestion.chunking import Orchestrator

   orchestrator = Orchestrator(result_file, "processed_docs.json")
   orchestrator.run()
   \```

3. **Initialize Vector Database:**
   \```python
   from src.vector_db import ResultRetriever

   retriever = ResultRetriever("processed_docs.json")
   retriever.initialize_components()
   \```

4. **Chat with Documentation:**
   \```python
   user_query = "How do I authenticate users?"
   results = retriever.retrieve(user_query)

   from src.generation.claude_assistant import Claude

   claude = Claude()
   claude.init()
   response = claude.get_augmented_response(user_query, results)
   print(response)
   \```
`
## ❤️‍🩹 Current Limitations

- Supports only text documentation in English 
- Limited to processing a single documentation set at a time
- No automatic database updates
- Depends on FireCrawl for initial document retrieval

## 🛣️ Roadmap

- [ ] Implement user interface (web/CLI)
- [ ] Implement structure-agnostic chunking logic to properly handle any documentation in Markdown
- [ ] Implement a basic search evaluation suite

## 📈 Performance Metrics

- Average query processing time: [Your metric here]
- Retrieval accuracy (e.g., NDCG@5): [Your metric here]
- Response coherence (based on human evaluation): [Your metric here]


## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [FireCrawl](https://firecrawl.dev/) for efficient web crawling
- [Chroma DB](https://www.trychroma.com/) for vector storage and retrieval
- [Anthropic](https://www.anthropic.com/) for Claude 3.5 Sonnet
- [OpenAI](https://openai.com/) for text embeddings
- [Cohere](https://cohere.ai/) for re-ranking capabilities

## 📞 Support

For any questions or issues, please [open an issue](https://github.com/yourusername/rag-4-docs/issues) or contact our support team at support@rag4docs.com.

---

Built with ❤️ by AZ
