# 🚀 Kollektiv - LLMs + Up-to-date knowledge

## 🌟 Overview

Kollektiv is a Retrieval-Augmented Generation (RAG) system designed for one purpose - allow you to chat with your
favorite docs (of libraries, frameworks, tools primarily) easily.

This project aims to allow LLMs to tap into the most up-to-date knowledge in 2 clicks so that you don't have to
worry about incorrect replies, hallucinations or inaccuracies when working with the best LLMs.

## ❓Why?
This project was born out of a **personal itch** - whenever a new feature of my favorite library comes up, I know I
can't rely on the LLM to help me build with it - because it simply doesn't know about it!

**The root cause** - LLMs lack access to the most recent documentation or private knowledge, as they are trained on a
set of data that was accumulated way back (sometimes more than a year ago).

**The impact** - hallucinations in answers, inaccurate, incorrect or outdated information, which directly decreases
productivity and usefulness of using LLMs

**But there is a better way...**

What if LLMs could tap into a source of up-to-date information on libraries, tools, frameworks you are building with?

Imagine your LLM could intelligently decide when it needs to check the documentation source and always provide an
accurate reply?

## 🎯 Goal
Meet Kollektiv -> an open-source RAG app that helps you easily:
- parse the docs of your favorite libraries
- efficiently stores and embeds them in a local vector storage
- sets up an LLM chat which you can rely on

**Note** this is v.0.1.* and reliability of the system can be characterized as following:
- in 50% of the times it works every time!

So do let me know if you are experiencing issues and I'll try to fix them.

## ⚙️ Key Features

- **🕷️ Intelligent Web Crawling**: Utilizes FireCrawl API to efficiently crawl and extract content from specified documentation websites.
- **🧠 Advanced Document Processing**: Implements custom chunking strategies to optimize document storage and retrieval.
- **🔍 Vector Search**: Employs Chroma DB for high-performance similarity search of document chunks.
- **🔄 Multi-Query Expansion**: Enhances search accuracy by generating multiple relevant queries for each user input.
- **📊 Smart Re-ranking**: Utilizes Cohere's re-ranking API to improve relevancy of search results
- **🤖 AI-Powered Responses**: Integrates with Claude 3.5 Sonnet to generate human-like, context-aware responses.
- **🧠 Dynamic system prompt**: Automatically summarizes the embedded documentation to improve RAG decision-making.

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
   git clone https://github.com/Twist333d/kollektiv.git
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
   ```bash
   poetry run python app.py
   ```
   or through a poetry alias:
   ```bash
   python app.py
   ```

## 💡 Usage

1. **Crawl Documentation:**

   Update the root url you want to parse. For example:
     ```python
     urls_to_crawl = ["https://docs.anthropic.com/en/docs/"]
     ```
      Ensure you include the url patterns of sub-pages you want to parse and exclude url patterns of sub-pages you
         don't want to parse:
     ```python
      "includePaths": ["/tutorials/*", "/how-tos/*", "/concepts/*"],
      "excludePaths": ["/community/*"],
     ```
      Set the maximum number of pages you want to crawl:
      ```python
       crawler.async_crawl_url(urls_to_crawl, page_limit=250)
      ```

2. **Chunk FireCrawl parsed docs:**

   Next step is to chunk all the parsed documents
   ```python
   poetry run python -m src.processing.chunking
   ```

3. **Configure basic parameters:**

   Set up the following parameters in the `app.py`:
   1. Whether to load only specified or all processed chunks in`PROCESSED_DATA_DIR`
   ```python
    docs = ["docs_anthropic_com_en_20240928_135426-chunked.json"]
    initializer = ComponentInitializer(reset_db=reset_db, load_all_docs=True, files=[])
   ```
   2. Whether to reset the database, which will clear all the data in local ChromaDB - use with caution. Defaults to
      false.
   ```python
   if __name__ == "__main__":
    main(debug=False, reset_db=False)
   ```
4. **Chat with documentation:**
   You can run application via the following command:
   ```python
   python app.py
   ```

## ❤️‍🩹 Current Limitations
- Only terminal UI (no Chainlit for now)
- Image data not supported - ONLY text-based embeddings.
- No automatic re-indexing of documents
- Basic chat flow supported
  - Either RAG tool is used or not
    - if a tool is used -> retrieves up to 5 most relevant documents (after re-ranking)

## 🛣️ Roadmap
For a brief roadmap please check out [project wiki page](https://github.com/Twist333d/kollektiv/wiki).

## 📈 Performance Metrics
Evaluation is currently done using `ragas` library. There are 2 key parts assessed:
1. End-to-end generation
   - Faithfulness
   - Answer relevancy
   - Answer correctness
2. Retriever (TBD)
   - Context recall
   - Context precision


## 📜 License


Kollektiv is licensed under a modified version of the Apache License 2.0. While it allows for free use, modification,
and distribution for non-commercial purposes, any commercial use requires explicit permission from the copyright owner.

- For non-commercial use: You are free to use, modify, and distribute this software under the terms of the Apache License 2.0.
- For commercial use: Please contact azuev@outlook.com to obtain a commercial license.

See the [LICENSE](LICENSE.md) file for the full license text and additional conditions.

## Project Renaming Notice

The project has been renamed from **OmniClaude** to **Kollektiv** to:
- avoid confusion / unintended copyright infringement of Anthropic
- emphasize the goal to become a tool to enhance collaboration through simplifying access to knowledge 
- overall cool name (isn't it?)

If you have any questions regarding the renaming, feel free to reach out.

## 🙏 Acknowledgements

- [FireCrawl](https://firecrawl.dev/) for superb web crawling
- [Chroma DB](https://www.trychroma.com/) for easy vector storage and retrieval
- [Anthropic](https://www.anthropic.com/) for Claude 3.5 Sonnet
- [OpenAI](https://openai.com/) for text embeddings
- [Cohere](https://cohere.ai/) for re-ranking capabilities

## 📞 Support

For any questions or issues, please [open an issue](https://github.com/Twist333d/kollektiv/issues)

---

Built with ❤️ by AZ