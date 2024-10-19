from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import cohere
import weave
from cohere import RerankResponse

from src.generation.summary_manager import SummaryManager
from src.utils.config import CHROMA_DB_DIR, COHERE_API_KEY, OPENAI_API_KEY, PROCESSED_DATA_DIR
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger

logger = get_logger()


class DocumentProcessor:
    """
    Process and manage document data.

    Args:
        filename (str): The name of the JSON file to load.

    Returns:
        list[dict]: A list of dictionaries containing the JSON data.

    Raises:
        FileNotFoundError: If the file cannot be found at the specified path.
        json.JSONDecodeError: If the file contains invalid JSON.
    """

    def __init__(self):
        self.processed_dir = PROCESSED_DATA_DIR

    def load_json(self, filename: str) -> list[dict]:
        """
        Load and parse JSON data from a specified file.

        Args:
            filename (str): Name of the file containing JSON data.

        Returns:
            list[dict]: A list of dictionaries parsed from the JSON file.

        Raises:
            FileNotFoundError: If the specified file cannot be found.
            JSONDecodeError: If the file contains invalid JSON.
        """
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


class VectorDBInterface(ABC):
    """Define an interface for vector database operations."""

    @abstractmethod
    def prepare_documents(self, chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
        """
        Prepare documents from given chunks.

        Args:
            chunks (list[dict[str, Any]]): A list of dictionaries where each dictionary contains various
            data attributes.

        Returns:
            dict[str, list[str]]: A dictionary where each key is a document identifier and the value is a list of
            processed text elements.

        Raises:
            ValueError: If the input chunks are not in the expected format.
        """
        pass

    @abstractmethod
    def add_documents(self, processed_docs: dict[str, list[str]]) -> None:
        """Add processed documents to the data store.

        Args:
            processed_docs (dict[str, list[str]]): A dictionary where the key is a document identifier and the value is
                                                   a list of processed text elements for that document.

        Returns:
            None

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    @abstractmethod
    def query(self, user_query: str | list[str], n_results: int = 10) -> dict[str, Any]:
        """
        Perform a query and return the results.

        Args:
            user_query (str | list[str]): The query string(s) to search for.
            n_results (int, optional): The number of results to return. Defaults to 10.

        Returns:
            dict[str, Any]: The query results in a dictionary format.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        pass

    @abstractmethod
    def reset_database(self) -> None:
        """
        Reset the database to its initial state.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        pass

    @abstractmethod
    def deduplicate_documents(self, search_results: dict[str, Any]) -> dict[str, Any]:
        """
        Handle the deduplication of search results.

        :param search_results: A dictionary containing search results where
                               keys are document IDs and values are document data.
                               The document data is represented as any type.

        :return: A dictionary with duplicate documents removed. The keys are
                 document IDs and values are the deduplicated document data.

        :raises ValueError: If the input search results are not a dictionary.
        """
        pass

    @abstractmethod
    def check_documents_exist(self, document_ids: list[str]) -> tuple[bool, list[str]]:
        """
        Check if the given documents exist in the database.

        Args:
            document_ids (list[str]): A list of document IDs to check.

        Returns:
            tuple[bool, list[str]]: A tuple containing a boolean indicating if all documents exist,
                                    and a list of IDs that do not exist.

        Raises:
            ValueError: If the document_ids list is empty.
        """
        pass


class VectorDB(VectorDBInterface):
    """
    Initializes the VectorDB class with embedding and OpenAI API configurations.

    Args:
        embedding_function (str): The name of the embedding function to use. Defaults to "text-embedding-3-small".
        openai_api_key (str): The OpenAI API key for authentication. Defaults to OPENAI_API_KEY.
    """

    def __init__(
        self,
        embedding_function: str = "text-embedding-3-small",
        openai_api_key: str = OPENAI_API_KEY,
    ):
        self.embedding_function = None
        self.client = None
        self.collection = None
        self.embedding_function_name = embedding_function
        self.openai_api_key = openai_api_key
        self.collection_name = "local-collection"
        self.summary_manager = SummaryManager()

        self._init()

    def _init(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)  # using default path for Chroma
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

    def prepare_documents(self, chunks: list[dict]) -> dict[str, list[str]]:
        """
        Prepare documents by extracting and combining headers and content.

        Args:
            chunks (list[dict]): A list of dictionaries where each dictionary contains the chunk data.

        Returns:
            dict[str, list[str]]: A dictionary with keys 'ids', 'documents', and 'metadatas' each containing a list.

        Raises:
            KeyError: If the required keys are missing from the dictionaries in chunks.
            TypeError: If the input is not a list of dictionaries.
        """
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
    def add_documents(self, json_data: list[dict], file_name: str) -> None:
        """
        Add documents from a given JSON list to the database, handling duplicates and generating summaries.

        Args:
            json_data (list[dict]): A list of dictionaries containing the document data.
            file_name (str): The name of the file from which the documents are being added.

        Returns:
            None

        Raises:
            Exception: If there is an error during the document preparation or addition process.
        """
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
        self.summary_manager.process_file(data=json_data, file_name=file_name)

    @base_error_handler
    def check_documents_exist(self, document_ids: list[str]) -> tuple[bool, list[str]]:
        """
        Check if documents exist.

        Args:
            document_ids (list[str]): The list of document IDs to check.

        Returns:
            tuple[bool, list[str]]: A tuple where the first element is a boolean indicating if all documents exist,
            and the second element is a list of missing document IDs.

        Raises:
            Exception: If an error occurs while checking the document existence.
        """
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
    def query(self, user_query: str | list[str], n_results: int = 10):
        """
        Query the collection to retrieve documents based on the user's query.

        Args:
            user_query (str | list[str]): A string or list of strings representing the user's query.
            n_results (int, optional): The number of results to retrieve. Defaults to 10.

        Returns:
            list: A list of search results matching the query.

        Raises:
            SomeSpecificException: If an error occurs while querying the collection.
        """
        query_texts = [user_query] if isinstance(user_query, str) else user_query
        search_results = self.collection.query(
            query_texts=query_texts, n_results=n_results, include=["documents", "distances", "embeddings"]
        )
        return search_results

    @base_error_handler
    def reset_database(self):
        """
        Reset the database by deleting and recreating the collection, and clearing summaries.

        Args:
            self: The instance of the class containing this method.

        Returns:
            None

        Raises:
            Exception: If there is an error while deleting or creating the collection, or clearing summaries.
        """
        # Delete collection
        self.client.delete_collection(self.collection_name)

        self.collection = self.client.create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )

        # Delete the summaries file
        self.summary_manager.clear_summaries()

        logger.info("Database reset successfully. ")

    def process_results_to_print(self, search_results: dict[str, Any]):
        """
        Process search results to a formatted string output.

        Args:
            search_results (dict[str, Any]): The search results containing documents and distances.

        Returns:
            list[str]: A list of formatted strings containing distances and corresponding documents.
        """
        documents = search_results["documents"][0]
        distances = search_results["distances"][0]

        output = []
        for docs, dist in zip(documents, distances, strict=True):
            output.append(f"Distance: {dist:.2f}\n\n{docs}")
        return output

    def deduplicate_documents(self, search_results: dict[str, Any]) -> dict[str, Any]:
        """
        Remove duplicate documents from search results based on unique chunk IDs.

        Args:
            search_results (dict[str, Any]): A dictionary containing lists of documents, distances, and IDs.

        Returns:
            dict[str, Any]: A dictionary of unique documents with their corresponding text and distance.

        Raises:
            None.
        """
        documents = search_results["documents"][0]
        distances = search_results["distances"][0]
        ids = search_results["ids"][0]

        unique_documents = {}

        for chunk_id, doc, distance in zip(ids, documents, distances, strict=True):
            if chunk_id not in unique_documents:
                unique_documents[chunk_id] = {"text": doc, "distance": distance}
        return unique_documents


class Reranker:
    """
    Initializes and manages a Cohere Client for document re-ranking.

    Args:
        cohere_api_key (str): API key for the Cohere service.
        model_name (str): Name of the model to use for re-ranking. Defaults to "rerank-english-v3.0".
    """

    def __init__(self, cohere_api_key: str = COHERE_API_KEY, model_name: str = "rerank-english-v3.0"):
        self.cohere_api_key = cohere_api_key
        self.model_name = model_name
        self.client = None

        self._init()

    def _init(self):
        try:
            self.client = cohere.ClientV2(api_key=self.cohere_api_key)
            logger.debug("Successfully initialized Cohere client")
        except Exception as e:
            logger.error(f"Error initializing Cohere client: {e}")
            raise

    def extract_documents_list(self, unique_documents: dict[str, Any]) -> list[str]:
        """
        Extract the 'text' field from each unique document.

        Args:
            unique_documents (dict[str, Any]): A dictionary where each value is a document represented as a dictionary
                                               with a 'text' field.

        Returns:
            list[str]: A list containing the 'text' field from each document.

        """
        # extract the 'text' field from each unique document
        document_texts = [chunk["text"] for chunk in unique_documents.values()]
        return document_texts

    def rerank(self, query: str, documents: dict[str, Any], return_documents=True) -> RerankResponse:
        """
        Rerank a list of documents based on their relevance to a given query.

        Args:
            query (str): The search query to rank the documents against.
            documents (dict[str, Any]): A dictionary containing documents to be reranked.
            return_documents (bool): A flag indicating whether to return the full documents. Defaults to True.

        Returns:
            RerankResponse: The reranked list of documents and their relevance scores.

        Raises:
            SomeSpecificException: If an error occurs during the reranking process.

        """
        # extract list of documents
        document_texts = self.extract_documents_list(documents)

        # get indexed results
        response = self.client.rerank(
            model=self.model_name, query=query, documents=document_texts, return_documents=return_documents
        )

        logger.debug(f"Received {len(response.results)} documents from Cohere.")
        return response


class ResultRetriever:
    """
    Initializes the ResultRetriever with a vector database and a reranker.

    Args:
        vector_db (VectorDB): The vector database used for querying documents.
        reranker (Reranker): The reranker used for reranking documents.
    """

    def __init__(self, vector_db: VectorDB, reranker: Reranker):
        self.db = vector_db
        self.reranker = reranker

    @base_error_handler
    @weave.op()
    def retrieve(self, user_query: str, combined_queries: list[str], top_n: int = None):
        """
        Retrieve and rank documents based on user query and combined queries.

        Args:
            user_query (str): The primary user query for retrieving documents.
            combined_queries (list[str]): A list of queries to combine for document retrieval.
            top_n (int, optional): The maximum number of top documents to return. Defaults to None.

        Returns:
            list: A list of limited, ranked, and relevant documents.

        Raises:
            DatabaseError: If there is an issue querying the database.
            RerankError: If there is an issue with reranking the documents.
        """
        start_time = time.time()  # Start timing

        # get expanded search results
        search_results = self.db.query(combined_queries)
        unique_documents = self.db.deduplicate_documents(search_results)
        logger.info(f"Search returned {len(unique_documents)} unique chunks")

        # rerank the results
        ranked_documents = self.reranker.rerank(user_query, unique_documents)

        # filter irrelevnat results
        filtered_results = self.filter_irrelevant_results(ranked_documents, relevance_threshold=0.1)

        # limit the number of returned chunks
        limited_results = self.limit_results(filtered_results, top_n=top_n)

        # calculate time
        end_time = time.time()  # End timing
        search_time = end_time - start_time
        logger.info(f"Search and reranking completed in {search_time:.3f} seconds")

        return limited_results

    def filter_irrelevant_results(
        self, response: RerankResponse, relevance_threshold: float = 0.1
    ) -> dict[int, dict[str, int | float | str]]:
        """
        Filter out results below a certain relevance threshold.

        Args:
            response (RerankResponse): The response containing the reranked results.
            relevance_threshold (float): The minimum relevance score required. Defaults to 0.1.

        Returns:
            dict[int, dict[str, int | float | str]]: A dictionary of relevant results with their index, text,
            and relevance score.

        Raises:
            None
        """
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

    def limit_results(self, ranked_documents: dict[str, Any], top_n: int = None) -> dict[str, Any]:
        """
        Limit the number of results based on the given top_n parameter.

        Args:
            ranked_documents (dict[str, Any]): A dictionary of documents with relevance scores.
            top_n (int, optional): The number of top results to return. Defaults to None.

        Returns:
            dict[str, Any]: The dictionary containing the top N ranked documents, or all documents if top_n is None.

        Raises:
            ValueError: If top_n is specified and is less than zero.
        """
        if top_n is not None and top_n < len(ranked_documents):
            # Sort the items by relevance score in descending order
            sorted_items = sorted(ranked_documents.items(), key=lambda x: x[1]["relevance_score"], reverse=True)

            # Take the top N items and reconstruct the dictionary
            limited_results = dict(sorted_items[:top_n])

            logger.info(
                f"Returning {len(limited_results)} most relevant results (out of total {len(ranked_documents)} "
                f"results)."
            )
            return limited_results

        logger.info(f"Returning all {len(ranked_documents)} results")
        return ranked_documents


def main():
    """
    Configure logging, reset the vector database, process JSON documents, and add them to the database.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        ValueError: If the JSON file is malformed or contains invalid data.
    """
    configure_logging()
    vector_db = VectorDB()
    vector_db.reset_database()

    file = "langchain-ai_github_io_langgraph_20240928_143920-chunked.json"
    reader = DocumentProcessor()
    documents = reader.load_json(file)
    vector_db.add_documents(documents, file)


if __name__ == "__main__":
    main()
