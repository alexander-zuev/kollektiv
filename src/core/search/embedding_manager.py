import chromadb.utils.embedding_functions as embedding_functions

from src.infrastructure.config.settings import settings
from src.models.vector_models import (
    CohereEmbeddingModelName,
    EmbeddingProvider,
    OpenAIEmbeddingModelName,
)


class EmbeddingManager:
    """Manages the embedding functions for the vector database."""

    def __init__(self, provider: EmbeddingProvider, model: CohereEmbeddingModelName | OpenAIEmbeddingModelName):
        self.provider = provider
        self.model = model
        self.embedding_function = self._get_embedding_function()

    def _get_embedding_function(self) -> embedding_functions.EmbeddingFunction:
        """Get the embedding function based on the provider."""
        if self.provider == EmbeddingProvider.COHERE:
            return self._get_cohere_embedding_function()
        elif self.provider == EmbeddingProvider.OPENAI:
            return self._get_openai_embedding_function()
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    def _get_cohere_embedding_function(self) -> embedding_functions.EmbeddingFunction:
        """Get the Cohere embedding function."""
        self.embedding_function = embedding_functions.CohereEmbeddingFunction(
            model_name=self.model,
            api_key=settings.cohere_api_key,
        )
        return self.embedding_function

    def _get_openai_embedding_function(self) -> embedding_functions.EmbeddingFunction:
        """Get the OpenAI embedding function."""
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key, model_name=self.model
        )
        return self.embedding_function

    def get_embedding_function(self) -> embedding_functions.EmbeddingFunction:
        """Get the embedding function."""
        return self.embedding_function
