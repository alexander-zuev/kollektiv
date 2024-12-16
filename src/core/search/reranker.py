from typing import Any

import cohere
from cohere.v2.types import V2RerankResponse

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings

logger = get_logger()


class Reranker:
    """
    Initializes and manages a Cohere Client for document re-ranking.

    Args:
        cohere_api_key (str): API key for the Cohere service.
        model_name (str): Name of the model to use for re-ranking. Defaults to "rerank-english-v3.0".
    """

    def __init__(self, cohere_api_key: str = settings.cohere_api_key, model_name: str = "rerank-english-v3.0"):
        self.cohere_api_key = cohere_api_key
        self.model_name = model_name
        self.client = None

        self._init()

    def _init(self) -> None:
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

    def rerank(self, query: str, documents: dict[str, Any], return_documents: bool = True) -> V2RerankResponse:
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
