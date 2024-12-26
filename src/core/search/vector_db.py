from __future__ import annotations

from typing import Any
from uuid import UUID

from src.core.search.embedding_manager import EmbeddingManager
from src.infra.decorators import base_error_handler
from src.infra.external.chroma_client import ChromaClient
from src.infra.logger import get_logger
from src.models.content_models import Chunk

logger = get_logger()


class VectorDB:
    """
    Initializes the VectorDB class with embedding and OpenAI API configurations.

    Args:
        embedding_function (str): The name of the embedding function to use. Defaults to "text-embedding-3-small".
        openai_api_key (str): The OpenAI API key for authentication. Defaults to OPENAI_API_KEY.
    """

    def __init__(
        self,
        chroma_client: ChromaClient,
        embedding_manager: EmbeddingManager,
    ):
        self.client = chroma_client
        self.embedding_function = embedding_manager.get_embedding_function()

    def _generate_collection_name(self, user_id: UUID) -> str:
        """Generate a collection name for a user."""
        return f"user_{str(user_id)}_collection"

    @base_error_handler
    async def create_collection(self, user_id: UUID) -> None:
        """Create a collection for a user."""
        collection_name = self._generate_collection_name(user_id)
        await self.client.create_collection(name=collection_name, embedding_function=self.embedding_function)
        logger.info(f"Created collection: {collection_name}")

    @base_error_handler
    async def delete_collection(self, user_id: UUID) -> None:
        """Delete a collection for a user."""
        collection_name = self._generate_collection_name(user_id)
        await self.client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")

    # TODO: processing of the chunks for vector storage should NOT be done here - move to chunk processor
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

    # TODO: add to storage should be clean, this should not have any business logic, just adding & emebding - move to chunk processor
    def add_documents(self, chunks: list[Chunk], user_id: UUID) -> None:
        """Add documents to the vector database."""
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
    async def query(self, user_query: str | list[str], n_results: int = 10) -> dict[str, Any]:
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
        collection_name = self._generate_collection_name(user_id)
        query_texts = [user_query] if isinstance(user_query, str) else user_query
        search_results = self.collection.query(
            query_texts=query_texts, n_results=n_results, include=["documents", "distances", "embeddings"]
        )
        return search_results

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
