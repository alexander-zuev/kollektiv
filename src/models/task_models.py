from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class KollektivTaskStatus(str, Enum):
    """Individual status of a Kollektiv task."""

    SUCCESS = "success"
    FAILED = "failed"
    # Can be expanded later to include more statuses


class KollektivTaskResult(BaseModel):
    """Base model for all Kollektiv task results. Must be returned by all tasks."""

    status: KollektivTaskStatus = Field(..., description="Status of the task")
    message: str = Field(..., description="Message of the task")
    data: dict[str, Any] | None = Field(None, description="Any additional data for the task")
