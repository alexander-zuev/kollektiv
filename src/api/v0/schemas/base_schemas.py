from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base API response for all API endpoints in Kollektiv API."""

    success: bool
    data: T | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    """Base API Error response for all API endpoints in Kollektiv API."""

    error: str
    code: int
    detail: str | None = None
