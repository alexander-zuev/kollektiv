from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base API response for all API endpoints in Kollektiv API."""

    success: bool
    data: T | None = None
    message: str | None = None


class ErrorCode(str, Enum):
    """Base api error code for all API endpoints in Kollektiv API."""

    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    CLIENT_ERROR = "CLIENT_ERROR"


class ErrorResponse(BaseModel):
    """Base api error response for all API endpoints in Kollektiv API."""

    code: ErrorCode = Field(..., description="Custom error code classification shared by FE and BE.")
    detail: str = Field(
        default="An unknown error occurred.",
        description="Error message for the client. All unknown errors should be properly parsed and grouped periodically.",
    )

    class Config:
        """Example configuration."""

        json_schema_extra = {
            "example": {
                "detail": "An error occurred while processing your request",
                "code": "SERVER_ERROR",  # Matches FE ERROR_CODES
            }
        }
