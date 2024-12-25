"""Holds all vector related models."""

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# Embedding models
class EmbeddingProvider(str, Enum):
    """Enum for the embedding providers."""

    OPENAI = "openai"
    COHERE = "cohere"


class CohereEmbeddingModelName(str, Enum):
    """Enum for the Cohere embedding models."""

    BASE_ENG = "embed-english-v3.0"
    BASE_MULTI = "embed-multilingual-v3.0"
    SMALL_ENG = "embed-english-v3.0-small"
    SMALL_MULTI = "embed-multilingual-v3.0-small"


class OpenAIEmbeddingModelName(str, Enum):
    """Enum for the OpenAI embedding models."""

    BASE = "text-embedding-3-large"
    SMALL = "text-embedding-3-small"


# Vector search & retrieval models
class UserQuery(BaseModel):
    """User query model."""

    user_id: UUID = Field(..., description="User ID")
    query: str | list[str] = Field(..., description="User query, which can be a single string or a list of strings")


class VectorSearchParams(BaseModel):
    """Default vector search params model."""

    n_results: int = Field(..., description="Number of results to retrieve")
    where: dict[str, Any] = Field(..., description="Filtering conditions for the search")
    where_document: dict[str, Any] = Field(..., description="Filtering conditions for the documents")
    include: list[Literal["documents", "metadatas", "distances"]] = Field(
        ..., description="Fields to include in the search results"
    )
