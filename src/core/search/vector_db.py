from __future__ import annotations

from typing import Any
from uuid import UUID

from chromadb.api.async_api import AsyncCollection, GetResult
from chromadb.errors import InvalidCollectionException

from src.core.search.embedding_manager import EmbeddingManager
from src.infra.decorators import base_error_handler
from src.infra.external.chroma_manager import ChromaManager
from src.infra.logger import get_logger
from src.models.content_models import Chunk
from src.models.vector_models import VectorCollection
from src.services.data_service import DataService

logger = get_logger()


class VectorDatabase:
    """Vector database responsible for storing and querying chunks."""

    def __init__(
        self,
        chroma_manager: ChromaManager,
        embedding_manager: EmbeddingManager,
        data_service: DataService,
    ):
        self.chroma_manager = chroma_manager
        self.embedding_manager = embedding_manager
        self.data_service = data_service

    async def _create_collection(self, user_id: UUID) -> VectorCollection:
        """Create a collection for a user."""
        # 1. Create collection in ChromaDB
        try:
            client = await self.chroma_manager.get_async_client()
            collection_name = VectorCollection(user_id=user_id).name
            collection = await client.create_collection(collection_name)
            logger.info(f"Created collection for user ID: {str(user_id)}")
        except ValueError:
            logger.exception(
                f"Collection for user ID {str(user_id)} already exists or name is invalid (should be a string)"
            )

        # 2. Save collection to Supabase
        # await self.data_service.save_collection(VectorCollection(user_id=user_id))
        return collection

    async def _get_existing_collection(self, user_id: UUID) -> AsyncCollection | None:
        """Get an existing collection for a user."""
        try:
            client = await self.chroma_manager.get_async_client()
            collection_name = VectorCollection(user_id=user_id).name
            collection = await client.get_collection(collection_name)
            logger.info(f"Collection for user ID {str(user_id)} exists")
            return collection
        except InvalidCollectionException:
            logger.info(f"Collection for user ID {str(user_id)} does not exist")
            return None

    async def get_or_create_collection(self, user_id: UUID) -> AsyncCollection:
        """Get or create a collection for a user."""
        existing_collection = await self._get_existing_collection(user_id)

        if existing_collection:
            return existing_collection
        else:
            new_collection = await self._create_collection(user_id)
            return new_collection

    async def delete_collection(self, user_id: UUID) -> None:
        """Delete a collection for a user."""
        collection_name = VectorCollection(user_id=user_id).name
        client = await self.chroma_manager.get_async_client()
        try:
            await client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except ValueError:
            logger.exception(f"Collection for user ID {str(user_id)} does not exist")

    # # TODO: processing of the chunks for vector storage should NOT be done here - move to chunk processor
    # def prepare_documents(self, chunks: list[dict]) -> dict[str, list[str]]:
    #     """
    #     Prepare documents by extracting and combining headers and content.

    #     Args:
    #         chunks (list[dict]): A list of dictionaries where each dictionary contains the chunk data.

    #     Returns:
    #         dict[str, list[str]]: A dictionary with keys 'ids', 'documents', and 'metadatas' each containing a list.

    #     Raises:
    #         KeyError: If the required keys are missing from the dictionaries in chunks.
    #         TypeError: If the input is not a list of dictionaries.
    #     """
    #     ids = []
    #     documents = []
    #     metadatas = []  # used for filtering

    #     for chunk in chunks:
    #         # extract headers
    #         data = chunk["data"]
    #         headers = data["headers"]
    #         header_text = " ".join(f"{key}: {value}" for key, value in headers.items() if value)

    #         # extract content
    #         content = data["text"]

    #         # combine
    #         combined_text = f"Headers: {header_text}\n\n Content: {content}"
    #         ids.append(chunk["chunk_id"])

    #         documents.append(combined_text)

    #         metadatas.append(
    #             {
    #                 "source_url": chunk["metadata"]["source_url"],
    #                 "page_title": chunk["metadata"]["page_title"],
    #             }
    #         )

    #     return {"ids": ids, "documents": documents, "metadatas": metadatas}

    # TODO: add to storage should be clean, this should not have any business logic, just adding & emebding - move to chunk processor
    # def add_documents(self, chunks: list[Chunk], user_id: UUID) -> None:
    #     """Add documents to the vector database."""
    #     processed_docs = self.prepare_documents(json_data)

    #     ids = processed_docs["ids"]
    #     documents = processed_docs["documents"]
    #     metadatas = processed_docs["metadatas"]

    #     # Check which documents are missing
    #     all_exist, missing_ids = self.check_documents_exist(ids)

    #     if all_exist:
    #         logger.info(f"All documents from {file_name} already loaded.")
    #     else:
    #         # Prepare data for missing documents only
    #         missing_indices = [ids.index(m_id) for m_id in missing_ids]
    #         missing_docs = [documents[i] for i in missing_indices]
    #         missing_metas = [metadatas[i] for i in missing_indices]

    #         # Add only missing documents
    #         self.collection.add(
    #             ids=missing_ids,
    #             documents=missing_docs,
    #             metadatas=missing_metas,
    #         )
    #         logger.info(f"Added {len(missing_ids)} new documents to ChromaDB.")

    #     # Generate summary for the entire file if not already present
    #     self.summary_manager.process_file(data=json_data, file_name=file_name)

    async def add_data(self, chunks: list[Chunk], user_id: UUID, fake_embeddings: bool = False) -> None:
        """Add data to the vector database."""
        collection = await self.get_or_create_collection(user_id)

        ids = [str(chunk.chunk_id) for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "source_url": str(chunk.source_url),
                "page_title": str(chunk.page_title),
                "source_id": str(chunk.source_id),
            }
            for chunk in chunks
        ]

        try:
            await collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                # embeddings=embeddings, # relying on ChromaDB to generate embeddings
            )
        except ValueError:
            logger.exception(
                f"Error adding documents to collection {collection.name}, please check the ids, documents, and metadatas"
            )

    async def get_data(self, user_id: UUID, lookup_ids: list[UUID]) -> GetResult:
        """Get data from the vector database by id."""
        collection = await self.get_or_create_collection(user_id)
        ids = [str(lookup_id) for lookup_id in lookup_ids]
        results = await collection.get(ids=ids)
        return results

    # def check_documents_exist(self, document_ids: list[str]) -> tuple[bool, list[str]]:
    #     """
    #     Check if documents exist.

    #     Args:
    #         document_ids (list[str]): The list of document IDs to check.

    #     Returns:
    #         tuple[bool, list[str]]: A tuple where the first element is a boolean indicating if all documents exist,
    #         and the second element is a list of missing document IDs.

    #     Raises:
    #         Exception: If an error occurs while checking the document existence.
    #     """
    #     try:
    #         # Get existing document ids from the db
    #         result = self.collection.get(ids=document_ids, include=[])
    #         existing_ids = set(result["ids"])

    #         # Find missing ids
    #         missing_ids = list(set(document_ids) - existing_ids)
    #         all_exist = len(missing_ids) == 0

    #         if missing_ids:
    #             logger.info(f"{len(missing_ids)} out of {len(document_ids)} documents are new and will be added.")
    #         return all_exist, missing_ids

    #     except Exception as e:
    #         logger.error(f"Error checking document existence: {e}")
    #         return False, document_ids

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
