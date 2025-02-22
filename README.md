# 🚀 Kollektiv - LLMs + Up-to-date knowledge

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/uv-package%20manager-blueviolet" alt="uv package manager" /></a>
  <a href="https://github.com/alexander-zuev/kollektiv/actions/workflows/ci_pipeline.yml"><img src="https://github.com/alexander-zuev/kollektiv/actions/workflows/ci_pipeline.yml/badge.svg" alt="CI" /></a>
  <a href="https://codecov.io/github/alexander-zuev/kollektiv"><img src="https://codecov.io/github/alexander-zuev/kollektiv/graph/badge.svg?token=FAT0JJNZG8" alt="codecov" /></a>
  <a href="https://github.com/alexander-zuev/kollektiv/blob/main/LICENSE.md"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License" /></a>
  <a href="https://github.com/alexander-zuev/kollektiv/graphs/commit-activity"><img src="https://img.shields.io/badge/Maintained-Active-green.svg" alt="Status" /></a>
</p>

> ⚠️ **Important Notice**
>
> Kollektiv is undergoing a major transformation for v0.2! Key updates in progress:
>
> - Complete architectural overhaul to a distributed system
> - Brand new React-based Chat UI
> - Enhanced RAG pipeline with Claude 3.5 Sonnet
> - Improved documentation and developer experience
>
> While the core functionality remains stable, some features and documentation might be outdated.
> The project is actively maintained, and updates are coming soon!
>
> **Current Status:**
> - ✅ Core RAG functionality works
> - ✅ API and worker services are stable
> - 🏗️ New UI in development
> - 📝 Documentation being updated

## v0.2 Release Plan
Kollektiv is getting ready for it's first major release. I'm going to update the documentation to reflect the new changes soon, but for now here is a sneak peak of what's coming:

- **New Chat UI**: Custom-built chat UI for talking with your docs
- **Architecture overhaul**: From the ground up rewrite of the codebase to align with proper distributed architecture - api, worker, KV store, vector DB, frontend UI
- **Improved RAG system**: Improved RAG system that provides more accurate replies for your queries
- **New documentation**: I'm going to add a lot of new documentation once the new version is released

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

**Note** this is v.0.1.6 and reliability of the system can be characterized as following:

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

- **Backend**: Python/FastAPI
- **Package Management**: UV
- **Task queue**: Arq
- **Storage**:
  - Supabase (auth/data)
  - ChromaDB (vectors)
  - Redis (queues/real-time)
- **LLM**:
  - Anthropic Claude 3.5 Sonnet (chat)
  - Cohere (re-ranking)

## 🚀 Quick Start

1. **Clone the repository:**

   ```bash
   git clone https://github.com/alexander-zuev/kollektiv.git
   cd kollektiv
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root with the following:

   ```bash
   FIRECRAWL_API_KEY="your_firecrawl_api_key"
   OPENAI_API_KEY="your_openai_api_key"
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   COHERE_API_KEY="your_cohere_api_key"
   ```

3. **Install dependencies:**
   ```bash
   #  create a virtual environment
   uv venv
   # activate the virtual environment
   source .venv/bin/activate
   # install dependencies with dev group
   uv sync --group dev
   ```

4. **Start the application:**
   ```bash
   # start docker services
   make up

   # start the api
   kollektiv api

   # start the workers
   kollektiv worker
   ```
5. **Deployment on Railway:**
Deployment requires settins the following environment variables:
- Service: api / worker
- Dockerfile path: `scripts/docker/Dockerfile`
- Build Command: `uv sync --frozen --no-dev`
- Start Command: `kollektiv $SERVICE`

## 📜 License

Kollektiv is licensed under the Apache License 2.0. See the [LICENSE](LICENSE.md) file for the full license text.

## 🥳 Acknowledgements

- [FireCrawl](https://firecrawl.dev/) for superb web crawling
- [Chroma DB](https://www.trychroma.com/) for easy vector storage and retrieval
- [Anthropic](https://www.anthropic.com/) for Claude 3.5 Sonnet
- [OpenAI](https://openai.com/) for text embeddings
- [Cohere](https://cohere.ai/) for re-ranking capabilities

## 📞 Support

For any questions or issues, please [open an issue](https://github.com/alexander-zuev/kollektiv/issues)

---

Built with ❤️ by AZ
