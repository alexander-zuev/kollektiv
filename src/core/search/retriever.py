import time
from typing import Any

from cohere.v2.types import V2RerankResponse

from src.core.search.reranker import Reranker
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.logger import get_logger

logger = get_logger()


class Retriever:
    """
    Initializes the Retriever with a vector database and a reranker.

    Args:
        vector_db (VectorDB): The vector database used for querying documents.
        reranker (Reranker): The reranker used for reranking documents.
    """

    def __init__(self, vector_db: VectorDB, reranker: Reranker):
        self.db = vector_db
        self.reranker = reranker

    async def retrieve(self, user_query: str, combined_queries: list[str], top_n: int | None) -> list[dict[str, Any]]:
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
        search_results = await self.db.query(combined_queries)
        if not search_results or not search_results.get("documents")[0]:
            logger.warning("No documents found in search results")
            return []

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
        self, response: V2RerankResponse, relevance_threshold: float = 0.1
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
