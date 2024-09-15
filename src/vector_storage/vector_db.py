from fileinput import filename
from pprint import pprint

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from typing import List, Dict, Any, Tuple, Union
import json
import os
import cohere

from generation.claude_assistant import ClaudeAssistant
from src.utils.config import OPENAI_API_KEY, COHERE_API_KEY, LOG_DIR, PROCESSED_DATA_DIR
from src.utils.logger import setup_logger
from src.generation.claude_assistant import QueryGenerator
from utils.decorators import error_handler

# Set up logger
logger = setup_logger("vector_db", os.path.join(LOG_DIR, "vector_db.log"))

class DocumentProcessor:
    def __init__(self, file_name):
        self.file_name = file_name
        self.file_path = os.path.join(PROCESSED_DATA_DIR, file_name)

    def load_json(self) -> List[Dict]:
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.error(f"File not found: {self.file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {self.file_path}")
            raise


class VectorDB:
    def __init__(self,
                 embedding_function: str = "text-embedding-3-small",
                 openai_api_key: str = OPENAI_API_KEY):
        self.embedding_function = None
        self.client = None
        self.collection = None
        self.embedding_function_name = embedding_function
        self.openai_api_key = openai_api_key
        self.collection_name = "local-collection"
        self.document_summaries = []

        self._init()

    def _init(self):
        self.client = chromadb.PersistentClient() # using default path for Chroma
        self._load_existing_summaries()
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.embedding_function_name
        )
        self.collection = self.client.get_or_create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )
        logger.info(f"Successfully initialized ChromaDb with collection: {self.collection_name}")
        if self.collection.count() == 0:
            logger.warning("No documents in the database")
        else:
            logger.info(f"A total number of documents in the database: {self.collection.count()}")

    @error_handler(logger)
    def _load_existing_summaries(self):
        summaries_file = os.path.join("src/vector_storage", "document_summaries.json")
        if os.path.exists(summaries_file):
            with open(summaries_file, 'r') as f:
                self.document_summaries = json.load(f)
            logger.info(f"Loaded {len(self.document_summaries)} existing document summaries")

    def prepare_documents(self, chunks: List[Dict]) -> Dict[str, List[str]]:
        ids = []
        documents = []
        metadatas = [] # used for filtering

        for chunk in chunks:
            # extract headers
            data = chunk['data']
            headers = data['headers']
            header_text = " ".join(f"{key}: {value}" for key, value in headers.items() if value)

            # extract content
            content = data['text']

            # combine
            combined_text = f"Headers: {header_text}\n\n Content: {content}"
            ids.append(chunk['chunk_id'])

            documents.append(combined_text)

            metadatas.append({
                'source_url': chunk['metadata']['source_url'],
                'page_title': chunk['metadata']['page_title'],
            })


        return {'ids': ids, 'documents': documents, 'metadatas': metadatas}

    @error_handler(logger)
    def add_documents(self, json_data: List[Dict], claude_assistant: ClaudeAssistant) -> str:

        processed_docs = self.prepare_documents(json_data)

        ids = processed_docs['ids']
        documents = processed_docs['documents']
        metadatas = processed_docs['metadatas']

        # check if documents exist
        all_exist, missing_ids = self.check_documents_exist(ids)

        if all_exist:
            logger.info("Documents with the same chunk ids exist in the database, skipping insertion")
            return

        else: # try to add all documents (handling only simplified case)
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            docs_n = len(ids)
            logger.info(f"Added {docs_n} documents to ChromaDB")

        # Generate summary for the entire document
        summary = claude_assistant.generate_document_summary(json_data)
        self.document_summaries.append(summary)

        # Update Claude's system prompt with all document summaries
        claude_assistant.update_system_prompt(self.document_summaries)

        # Save updated summaries
        self._save_summaries()
        return summary


    @error_handler(logger)
    def _save_summaries(self):
        summaries_file = os.path.join("src/vector_storage", "document_summaries.json")
        with open(summaries_file, 'w') as f:
            json.dump(self.document_summaries, f, indent=2)
        logger.info(f"Saved {len(self.document_summaries)} document summaries")

    @error_handler(logger)
    def get_document_summaries(self) -> List[str]:
        return list(self.document_summaries.values())


    @error_handler(logger)
    def check_documents_exist(self, document_ids: List[str]) -> Tuple[bool, List[str]]:
        """Checks, if chunks are already added to the database based on chunk ids"""

        try:
            # Get all current document ids from the db
            result = self.collection.get(
                ids=document_ids,
                include=[]
            )

            # get the existing set of ids
            existing_ids = set(result['ids'])

            # find missing ids
            missing_ids = list(set(document_ids) - existing_ids)

            all_exist = len(missing_ids) == 0

            if not all_exist:
                logger.warning("Found missing chunks by chunk ID, reloading the full documents list.")
            return all_exist, missing_ids

        except Exception as e:
            logger.error(f"Error checking document existence {e}")
            return False, document_ids

    @error_handler(logger)
    def query(self, user_query: Union[str, List[str]], n_results: int = 5):
        """
        Handles both a single query and multiple queris
        """
        if isinstance(user_query, str):
            query_texts = [user_query]
        if isinstance(user_query, list):
            query_texts = user_query
        search_results = self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            include=['documents', 'distances', 'embeddings']
        )
        return search_results

    @error_handler(logger)
    def reset_database(self):
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )
        self.document_summaries = []
        logger.info("Database reset")

    def process_results_to_print(self, search_results: Dict[str, Any]):
        documents = search_results['documents'][0]
        distances = search_results['distances'][0]

        output = []
        for docs, dist in zip(documents, distances):
            output.append(f"Distance: {dist:.2f}\n\n{docs}")
        return output

    def deduplicate_documents(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        documents = search_results['documents'][0]
        distances = search_results['distances'][0]
        ids = search_results['ids'][0]

        unique_documents = {}

        for chunk_id, doc, distance in zip(ids, documents, distances):
            if chunk_id not in unique_documents:
                unique_documents[chunk_id] = {
                    'text' : doc,
                    'distance' : distance
                }
        return unique_documents


class Reranker:
    def __init__(self, cohere_api_key: str = COHERE_API_KEY, model_name: str = 'rerank-english-v3.0'):
        self.cohere_api_key = cohere_api_key
        self.model_name = model_name
        self.client = None

        self._init()


    def _init(self):
        try:
            self.client = cohere.Client(os.getenv("COHERE_API_KEY"))
            logger.info("Successfully initialized Cohere client")
        except Exception as e:
            logger.error(f"Error initializing Cohere client: {e}")
            raise

    def extract_documents_list(self, unique_documents: Dict[str, Any]) -> List[str]:
        """
        Prepares the unique documents list for processing by Cohere.
        """
        # extract the 'text' field from each unique document
        document_texts = [chunk['text'] for chunk in unique_documents.values()]
        return document_texts

    def filter_irrelevant_results(self, response: Dict[str, Any], relevance_threshold: float =
    0.01) \
            -> (
            Dict)[
        str, Any]:
        """ Filters out irrelevant result from Cohere reranking"""
        relevant_results = {}

        for result in response.results:
            relevance_score = result.relevance_score
            index = result.index
            text = result.document.text

            if relevance_score >= relevance_threshold:
                relevant_results[index] = {
                    'text' : text,
                    'index' : index,
                    'relevant_score' : relevance_score,
                }

        return relevant_results


    def rerank(self, query: str, documents: Dict[str, Any], relevance_threshold: float = 0.01, return_documents=True):
        """
        Use Cohere rerank API to score and rank documents based on the query.
        Excludes irrelevant documents.
        :return: list of documents with relevance scores
        """
        # extract list of documents
        document_texts = self.extract_documents_list(documents)

        # get indexed results
        response = self.client.rerank(
            model = self.model_name,
            query = query,
            documents = document_texts,
            return_documents=True
        )

        logger.info(f"Received {len(response.results)} documents from Cohere.")
        # pprint(response.results)

        # filter irrelevant results
        logger.info(f"Filtering out the results with less than {relevance_threshold} relevance "
                    f"score")
        relevant_results = self.filter_irrelevant_results(response, relevance_threshold)
        logger.info(f"{len(relevant_results)} documents remaining after filtering.")

        return relevant_results

class ResultRetriever:
    def __init__(self, vector_db: VectorDB, reranker: Reranker):
        self.file_name = filename
        self.db = vector_db
        self.reranker = reranker


    def retrieve(self, user_query: str, combined_queries: List[str]):
        """Given the user query run the full end to end flow"""
        try:

            # get expanded search results
            search_results = self.db.query(combined_queries)
            unique_documents = self.db.deduplicate_documents(search_results)
            logger.debug(f"Debugging ranked documents {unique_documents}")

            # rerank the results
            ranked_documents = self.reranker.rerank(user_query, unique_documents)
            logger.debug(f"Debugging ranked documents {ranked_documents}")

            logger.debug("End to end flow works")
            return ranked_documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise


def main():
    vector_db = VectorDB()
    vector_db.reset_database()

if __name__ == "__main__":
    main()