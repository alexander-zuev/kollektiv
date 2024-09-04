# Feature
Implementation of Chroma DB and vector embeddings for the chunked docs

# Examples
Example from Anthropic's RAG tutorial:
```python
import os
import pickle
import json
import numpy as np
import voyageai

class VectorDB:
    def __init__(self, name, api_key=None):
        if api_key is None:
            api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client(api_key=api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/vector_db.pkl"

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

    def _embed_and_store(self, texts, data):
        batch_size = 128
        result = [
            self.client.embed(
                texts[i : i + batch_size],
                model="voyage-2"
            ).embeddings
            for i in range(0, len(texts), batch_size)
        ]
        self.embeddings = [embedding for batch in result for embedding in batch]
        self.metadata = data

    def search(self, query, k=5, similarity_threshold=0.75):
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.client.embed([query], model="voyage-2").embeddings[0]
            self.query_cache[query] = query_embedding

        if not self.embeddings:
            raise ValueError("No data loaded in the vector database.")

        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1]
        top_examples = []
        
        for idx in top_indices:
            if similarities[idx] >= similarity_threshold:
                example = {
                    "metadata": self.metadata[idx],
                    "similarity": similarities[idx],
                }
                top_examples.append(example)
                
                if len(top_examples) >= k:
                    break
        self.save_db()
        return top_examples

    def save_db(self):
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "query_cache": json.dumps(self.query_cache),
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as file:
            pickle.dump(data, file)

    def load_db(self):
        if not os.path.exists(self.db_path):
            raise ValueError("Vector database file not found. Use load_data to create a new database.")
        with open(self.db_path, "rb") as file:
            data = pickle.load(file)
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        self.query_cache = json.loads(data["query_cache"])
```

I need to define something similar but using ChromaDB and vector embeddings from OpenAI.

## Scope
- Create a ChromaDB database
- Load chunks into the database
- Generate embeddings using OpenAI's API
- Store data in ChromaDB
- Load the database
- Save the database

## Inputs
- Chunks which have the following structure
- File path (example): src/document_ingestion/data/processed/processed_supabase_docs_20240901_193122.json
```json
{
  "metadata": {
    "input_file": "supabase.com_docs__20240826_212435.json",
    "timestamp": "2024-09-01T19:31:23.720577",
    "total_documents": 25,
    "total_chunks": 2000
  },
  "chunks": [
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
    {
      "source_url": "https://supabase.com/docs/reference/python/initializing",
      "headers": {
        "H1": "",
        "H2": "",
        "H3": "Install with PyPi[#](#install-with-pypi)"
      },
      "content": "\nInstalling----------\n\n### Install with PyPi[#](#install-with-pypi)\n\nYou can install supabase-py via the terminal. (for > Python 3.7)\n\nPIPConda\n\nTerminal\n\n`     _10  pip install supabase      `\n\n* * *\n* * *\n",
      "chunk_id": "4585735c-b033-4081-bd39-4969af397174",
      "token_count": 62,
      "has_code_block": false
    },
    {
      "source_url": "https://supabase.com/docs/reference/python/initializing",
      "headers": {
        "H1": "",
        "H2": "",
        "H3": "Parameters"
      },
```
## Outputs

- A ChromaDB instance containing:
  - Document chunks
  - Generated embeddings
  - Associated metadata
- Search functionality
- Multi-query functionality
- Re-ranking functionality
- Final output formatting

## High-level Approach

1. Set up ChromaDB client
2. Create a collection for storing document chunks
3. Process input JSON file
4. Generate embeddings using in-built Chroma API
5. Implement search functionality using ChromaDB's query methods
6. Implement multi-query expansion using gpt-4o-mini
7. Implement re-ranking using Cohere API
6. Provide methods to save and load the database state

## Component Structure

1. `DocumentProcessor` class:
   - load_chunks() Loads the data
   - prepare_documents() Pre-processes the chunks to be ready for feeding into the vector db (headers + content)
2. `VectorDB` class:
   - Initialize ChromaDB client and collection
   - Methods:
     - `init` - initialize chromadb client with persistent storage
     - `add_documents` - loads the documents into the database
     - `query()` - use query func
3. `LLMClient` - initiates llm client to be used for this classs
4. `QueryExpander` - expands the original query
   - Uses LLMClient to expand queries
   - Unifies the resulting documents
5. `ReRanker` - uses Cohere API to re-rank the results
6. `ResultsRetriever` - orchestrates end to end flow
   - Input: user query
   - Steps:
     - Generate multi-queries
     - Generate multiple documents
     - Unify documents
     - Passes them to re-ranker
     - Prepares the output list
   - Output:
     - Outputs the most relevant documents