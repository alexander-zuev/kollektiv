import json
import os
import time
from typing import Any

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import cohere

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import CHROMA_DB_DIR, COHERE_API_KEY, OPENAI_API_KEY, PROCESSED_DATA_DIR, VECTOR_STORAGE_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


class DocumentProcessor:
    def __init__(self):
        self.processed_dir = PROCESSED_DATA_DIR

    def load_json(self, filename: str) -> list[dict]:
        try:
            filepath = os.path.join(self.processed_dir, filename)
            with open(filepath) as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {filename}")
            raise


class VectorDB:
    def __init__(self, embedding_function: str = "text-embedding-3-small", openai_api_key: str = OPENAI_API_KEY):
        self.embedding_function = None
        self.client = None
        self.collection = None
        self.embedding_function_name = embedding_function
        self.openai_api_key = openai_api_key
        self.collection_name = "local-collection"
        self.document_summaries = {}

        self._init()

    def _init(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)  # using default path for Chroma
        self._load_existing_summaries()
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key, model_name=self.embedding_function_name
        )
        self.collection = self.client.get_or_create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )
        logger.info(
            f"Successfully initialized ChromaDb with collection: {self.collection_name}\n with "
            f"{self.collection.count()} documents (chunks)"
        )

    @base_error_handler
    def _load_existing_summaries(self):
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        if os.path.exists(summaries_file):
            try:
                with open(summaries_file) as f:
                    self.document_summaries = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to load document summaries: {e}")
                self.document_summaries = {}
        else:
            self.document_summaries = {}

    def prepare_documents(self, chunks: list[dict]) -> dict[str, list[str]]:
        ids = []
        documents = []
        metadatas = []  # used for filtering

        for chunk in chunks:
            # extract headers
            data = chunk["data"]
            headers = data["headers"]
            header_text = " ".join(f"{key}: {value}" for key, value in headers.items() if value)

            # extract content
            content = data["text"]

            # combine
            combined_text = f"Headers: {header_text}\n\n Content: {content}"
            ids.append(chunk["chunk_id"])

            documents.append(combined_text)

            metadatas.append(
                {
                    "source_url": chunk["metadata"]["source_url"],
                    "page_title": chunk["metadata"]["page_title"],
                }
            )

        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    @base_error_handler
    def add_documents(self, json_data: list[dict], claude_assistant: ClaudeAssistant, file_name: str) -> str | None:
        processed_docs = self.prepare_documents(json_data)

        ids = processed_docs["ids"]
        documents = processed_docs["documents"]
        metadatas = processed_docs["metadatas"]

        # Check which documents are missing
        all_exist, missing_ids = self.check_documents_exist(ids)

        if all_exist:
            logger.info(f"All documents from {file_name} already loaded.")
        else:
            # Prepare data for missing documents only
            missing_indices = [ids.index(m_id) for m_id in missing_ids]
            missing_docs = [documents[i] for i in missing_indices]
            missing_metas = [metadatas[i] for i in missing_indices]

            # Add only missing documents
            self.collection.add(
                ids=missing_ids,
                documents=missing_docs,
                metadatas=missing_metas,
            )
            logger.info(f"Added {len(missing_ids)} new documents to ChromaDB.")

        # Generate summary for the entire file if not already present
        if file_name in self.document_summaries:
            result = self.document_summaries[file_name]
            logger.info(f"Loading existing summary for {file_name}.")
        else:
            logger.info(f"Summary for {file_name} not found, generating new one.")
            result = claude_assistant.generate_document_summary(json_data)
            result["filename"] = file_name
            self.document_summaries[file_name] = result

        # Save updated summaries
        self._save_summaries()
        return result

    @base_error_handler
    def _save_summaries(self):
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        try:
            with open(summaries_file, "w") as f:
                json.dump(self.document_summaries, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save document summaries: {e}")

    @base_error_handler
    def get_document_summaries(self) -> list[str]:
        return list(self.document_summaries.values())

    @base_error_handler
    def check_documents_exist(self, document_ids: list[str]) -> tuple[bool, list[str]]:
        """Checks if chunks are already added to the database based on chunk ids"""
        try:
            # Get existing document ids from the db
            result = self.collection.get(ids=document_ids, include=[])
            existing_ids = set(result["ids"])

            # Find missing ids
            missing_ids = list(set(document_ids) - existing_ids)
            all_exist = len(missing_ids) == 0

            if missing_ids:
                logger.info(f"{len(missing_ids)} out of {len(document_ids)} documents are new and will be added.")
            return all_exist, missing_ids

        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False, document_ids

    @base_error_handler
    def query(self, user_query: str | list[str], n_results: int = 5):
        """
        Handles both a single query and multiple queris
        """
        if isinstance(user_query, str):
            query_texts = [user_query]
        if isinstance(user_query, list):
            query_texts = user_query
        search_results = self.collection.query(
            query_texts=query_texts, n_results=n_results, include=["documents", "distances", "embeddings"]
        )
        return search_results

    @base_error_handler
    def reset_database(self):
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )
        self.document_summaries = {}
        # Delete the summaries file
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        if os.path.exists(summaries_file):
            os.remove(summaries_file)
            logger.info("Document summaries cleared.")
        logger.info("Database reset.")

    def process_results_to_print(self, search_results: dict[str, Any]):
        documents = search_results["documents"][0]
        distances = search_results["distances"][0]

        output = []
        for docs, dist in zip(documents, distances, strict=True):
            output.append(f"Distance: {dist:.2f}\n\n{docs}")
        return output

    def deduplicate_documents(self, search_results: dict[str, Any]) -> dict[str, Any]:
        documents = search_results["documents"][0]
        distances = search_results["distances"][0]
        ids = search_results["ids"][0]

        unique_documents = {}

        for chunk_id, doc, distance in zip(ids, documents, distances, strict=True):
            if chunk_id not in unique_documents:
                unique_documents[chunk_id] = {"text": doc, "distance": distance}
        return unique_documents


class Reranker:
    def __init__(self, cohere_api_key: str = COHERE_API_KEY, model_name: str = "rerank-english-v3.0"):
        self.cohere_api_key = cohere_api_key
        self.model_name = model_name
        self.client = None

        self._init()

    def _init(self):
        try:
            self.client = cohere.Client(self.cohere_api_key)
            logger.debug("Successfully initialized Cohere client")
        except Exception as e:
            logger.error(f"Error initializing Cohere client: {e}")
            raise

    def extract_documents_list(self, unique_documents: dict[str, Any]) -> list[str]:
        """
        Prepares the unique documents list for processing by Cohere.
        """
        # extract the 'text' field from each unique document
        document_texts = [chunk["text"] for chunk in unique_documents.values()]
        return document_texts

    def filter_irrelevant_results(self, response: dict[str, Any], relevance_threshold: float = 0.1) -> (dict)[str, Any]:
        """Filters out irrelevant result from Cohere reranking"""
        relevant_results = {}

        for result in response.results:
            relevance_score = result.relevance_score
            index = result.index
            text = result.document.text

            if relevance_score >= relevance_threshold:
                relevant_results[index] = {
                    "text": text,
                    "index": index,
                    "relevance_score": relevance_score,
                }

        return relevant_results

    def rerank(self, query: str, documents: dict[str, Any], relevance_threshold: float = 0.1, return_documents=True):
        """
        Use Cohere rerank API to score and rank documents based on the query.
        Excludes irrelevant documents.
        :return: list of documents with relevance scores
        """
        # extract list of documents
        document_texts = self.extract_documents_list(documents)

        # get indexed results
        response = self.client.rerank(
            model=self.model_name, query=query, documents=document_texts, return_documents=return_documents
        )

        logger.debug(f"Received {len(response.results)} documents from Cohere.")
        # pprint(response.results)

        # filter irrelevant results
        logger.debug(f"Filtering out the results with less than {relevance_threshold} relevance " f"score")
        relevant_results = self.filter_irrelevant_results(response, relevance_threshold)
        logger.info(f"{len(relevant_results)} documents remaining after re-ranking.")

        return relevant_results


class ResultRetriever:
    def __init__(self, vector_db: VectorDB, reranker: Reranker):
        self.db = vector_db
        self.reranker = reranker

    def retrieve(self, user_query: str, combined_queries: list[str]):
        """Returns ranked documents based on the user query"""
        try:
            start_time = time.time()  # Start timing

            # get expanded search results
            search_results = self.db.query(combined_queries)
            unique_documents = self.db.deduplicate_documents(search_results)
            logger.info(f"Search returned {len(unique_documents)} unique chunks")

            # rerank the results
            ranked_documents = self.reranker.rerank(user_query, unique_documents)
            logger.debug(f"Debugging ranked documents {ranked_documents}")

            end_time = time.time()  # End timing
            search_time = end_time - start_time
            logger.info(f"Search and reranking completed in {search_time:.3f} seconds")
            return ranked_documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise


def main():
    configure_logging()
    vector_db = VectorDB()
    vector_db.reset_database()
    claude_assistant = ClaudeAssistant(vector_db=vector_db)

    file = "langchain-ai_github_io_langgraph_20240928_143920-chunked.json"
    reader = DocumentProcessor()
    documents = reader.load_json(file)
    vector_db.add_documents(documents, claude_assistant, file)


if __name__ == "__main__":
    main()
