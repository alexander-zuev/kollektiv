from typing import Generic, TypeVar

from pydantic import BaseModel

from src.models.content_models import SourceAPIResponse

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base API response for all API endpoints in Kollektiv API."""

    success: bool
    data: T | None = None
    message: str | None = None


class SourceResponse(BaseResponse[SourceAPIResponse]):
    """Concrete response model for source operations."""

    pass


class ErrorResponse(BaseModel):
    """Base API Error response for all API endpoints in Kollektiv API."""

    error: str
    code: int
    detail: str | None = None
