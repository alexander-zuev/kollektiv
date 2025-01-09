from typing import Literal

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Response for the health check endpoint."""

    status: Literal["operational", "degraded", "down"] = Field(..., description="The health status of the system")
    message: str = Field(..., description="A message describing the health status of the system")
