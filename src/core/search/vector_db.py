# TODO: Implement user-specific context (use user_id) for managing vector data to avoid conflicts between users.
# TODO: Batch vector insertions to improve performance when handling multiple embeddings at once.
# TODO: Support concurrent vector lookups using async or multi-threading to enhance retrieval performance.
# TODO: Ensure embeddings are stored in the background and notify users when embedding is complete.
# TODO: Add logging and error handling for vector database operations.
# TODO: Consider introducing a queuing system to handle multiple embeddings requests efficiently.
# TODO: 10x SPEED
# TODO: 10x ACCURACY
# TODO: consider transition to Supabase Vector
from __future__ import annotations

import json
import os
from typing import Any

import chromadb
import chromadb.utils.embedding_functions as embedding_functions

from src.core.chat.summary_manager import SummaryManager
from src.infrastructure.common.decorators import base_error_handler
from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings

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

    def __init__(self) -> None:
        self.processed_dir = settings.processed_data_dir

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


class VectorDB:
    """
    Initializes the VectorDB class with embedding and OpenAI API configurations.

    Args:
        embedding_function (str): The name of the embedding function to use. Defaults to "text-embedding-3-small".
        openai_api_key (str): The OpenAI API key for authentication. Defaults to OPENAI_API_KEY.
    """

    def __init__(
        self,
        embedding_function: str = "text-embedding-3-small",
        openai_api_key: str = settings.openai_api_key,
    ):
        self.embedding_function = None
        self.client = None
        self.collection = None
        self.embedding_function_name = embedding_function
        self.openai_api_key = openai_api_key
        self.collection_name = "local-collection"
        self.summary_manager = SummaryManager()

        self._init()

    def _init(self) -> None:
        """Initialize ChromaDB client and embedding function."""
        self.client = chromadb.PersistentClient(path=str(settings.chroma_db_dir))
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key, model_name=self.embedding_function_name
        )
        self.collection = self.client.get_or_create_collection(
            self.collection_name, embedding_function=self.embedding_function
        )
        logger.info(
            f"Successfully initialized ChromaDb with collection: {self.collection_name}\n"
            f"with {self.collection.count()} documents (chunks)"
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
    def add_documents(self, json_data: list[dict], file_name: str) -> dict[str, str]:
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
