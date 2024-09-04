from pprint import pprint

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from typing import List, Dict, Any
import json
import os
from openai import OpenAI

from src.utils.config import OPENAI_API_KEY, PERSIST_DIRECTORY, LOG_DIR, PROCESSED_DATA_DIR
from src.utils.logger import setup_logger

# Set up logger
logger = setup_logger("vector_db", os.path.join(LOG_DIR, "vector_db.log"))

class DocumentProcessor:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.file_path = os.path.join(PROCESSED_DATA_DIR, file_name)

    def load_json(self) -> List[Dict]:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return data['chunks']
        except FileNotFoundError:
            logger.error(f"File not found: {self.file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {self.file_path}")
            raise

    def prepare_documents(self, chunks: List[Dict]) -> Dict[str, List[str]]:
        ids =[]
        documents = []
        for chunk in chunks:
            # extract headers
            headers = chunk['headers']
            header_text = " ".join(f"{key}: {value}" for key, value in headers.items() if value)

            # extract content
            content = chunk['content']

            # combine
            combined_text = f"Headers: {header_text}\n\n: Content{content}"
            ids.append(chunk['chunk_id'])

            documents.append(combined_text)

        return {'ids': ids, 'documents': documents}

class VectorDB:
    def __init__(self,
                 persist_dir: str = PERSIST_DIRECTORY,
                 collection_name: str = "supabase_collection",
                 embedding_function: str = "text-embedding-3-small",
                 openai_api_key: str = OPENAI_API_KEY):
        self.embedding_function = None
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embedding_function_name = embedding_function
        self.openai_api_key = openai_api_key

    def init(self):
        try:
            self.client = chromadb.PersistentClient() # using default path for Chroma
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.openai_api_key,
                model_name=self.embedding_function_name
            )
            self.collection = self.client.get_or_create_collection(
                "supabase-collection", embedding_function=self.embedding_function
            )
            logger.info(f"Successfully initialized ChromaDb with collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise

    def add_documents(self, processed_docs: Dict[str, List[str]]) -> None:
        try:
            ids = processed_docs['ids']
            documents = processed_docs['documents']
            self.collection.add(
                ids=ids,
                documents=documents
            )
            docs_n = len(ids)
            logger.info(f"Added {docs_n} documents to ChromaDB")
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise

    def query(self, user_query: str, n_results: int = 5):
        search_results = self.collection.query(
            query_texts=[user_query],
            n_results=n_results,
            include=['documents', 'distances', 'embeddings']
        )
        return search_results

    def process_query_results(self, search_results: Dict[str, Any]):
        documents = search_results['documents'][0]
        distances = search_results['distances'][0]

        output = []
        for docs, dist in zip(documents, distances):
            output.append(f"Distance: {dist:.2f}\n\n{docs}")
        return output

class OpenAIClient:
    def __init__(self, api_key: str = OPENAI_API_KEY, model_name: str = 'gpt-4o-mini'):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None

    def init(self):
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("Successfully initialized OpenAI client")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            raise

    def generate_multi_query(self, user_query: str, model: str) -> List[str]:
        prompt = """
        You are a meticoulous, accurate, and knowledgeable AI assistant.
        You are helping users retrieve relevan information from a vector database.
        For the given user question, formulate up to 3 related, relevant questions to assist in finding the 
        information.
        
        Requirements to follow:
        - Provide concise, single-topic questions (without compounding sentences) that cover various aspects of 
        the topic.
        - Ensure each question is complete and directly related to the original inquiry.
        - List each question on a separate line without numbering.
        """

        try:
            messages = [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': user_query},
            ]
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            content = response.choices[0].message.content
            content = content.split('\n')
            return content
        except Exception as e:
            logger.error(f"Error generating OpenAI completion: {e}")
            raise

# Test usage
doc_processor = DocumentProcessor("processed_supabase_docs_20240901_193122.json")
docs = doc_processor.load_json()
processed_docs = doc_processor.prepare_documents(docs)

# load documents into db
db = VectorDB()
db.init()
db.add_documents(processed_docs)

# query
user_query = input("Input your query here: ")
# search_result = db.query(user_query)
# processed_results = db.process_query_results(search_result)
# pprint(processed_results)

# Generate multi-queries
openai_client = OpenAIClient()
openai_client.init()
multiple_queries = openai_client.generate_multi_query(user_query, model='gpt-4o-mini')
for query in multiple_queries:
    print(query)

# Get additional documents

# Unify documents

# Re-rank

# Send to the generation