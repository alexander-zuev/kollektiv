"""API client for Kollektiv services."""

import httpx
from fastapi import HTTPException, status

from src.api.routes import Routes
from src.api.v0.content.schemas import (
    AddContentSourceRequest,
    SourceAPIResponse,
)
from src.infrastructure.config.logger import get_logger
from src.infrastructure.config.settings import API_HOST, API_PORT

logger = get_logger()


class KollektivAPIClient:
    """Client for interacting with Kollektiv API endpoints."""

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize API client.

        Args:
            base_url: Optional custom base URL. Defaults to local API URL.
        """
        self.base_url = base_url or f"http://{API_HOST}:{API_PORT}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def add_source(self, request: AddContentSourceRequest) -> SourceAPIResponse:
        """Add a new content source.

        Args:
            request: Content source details

        Returns:
            ContentSourceResponse: Created content source

        Raises:
            HTTPException: If the request fails
        """
        try:
            response = await self.client.post(
                f"{self.base_url}{Routes.V0.BASE}{Routes.V0.Content.SOURCES}",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return SourceAPIResponse.model_validate(response.json())
        except httpx.HTTPError as e:
            logger.error(f"Failed to add source: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add source: {str(e)}",
            ) from e

    async def list_sources(self) -> list[SourceAPIResponse]:
        """List all content sources."""
        try:
            response = await self.client.get(f"{self.base_url}{Routes.V0.Content.SOURCES}")
            response.raise_for_status()
            return [SourceAPIResponse.model_validate(item) for item in response.json()]
        except httpx.HTTPError as e:
            logger.error(f"Failed to list sources: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list sources: {str(e)}",
            ) from e

    async def delete_source(self, source_id: str) -> None:
        """Delete a content source."""
        try:
            response = await self.client.delete(
                f"{self.base_url}{Routes.V0.Content.SOURCE.format(source_id=source_id)}"
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete source: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete source: {str(e)}",
            ) from e
