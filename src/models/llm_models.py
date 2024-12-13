from typing import Any, Literal

from pydantic import BaseModel, Field


class CacheControl(BaseModel):
    """Cache control for Anthropic API."""

    type: Literal["ephemeral"] = "ephemeral"


class ToolInputSchema(BaseModel):
    """Base model for tool input schema validation."""

    type: Literal["object"] = "object"
    properties: dict[str, Any]
    required: list[str] | None = None


class Tool(BaseModel):
    """Tool definition for LLM following Anthropic's API spec."""

    name: str = Field(..., description="Tool name. Must match regex ^[a-zA-Z0-9_-]{1,64}$")
    description: str = Field(..., description="Detailed description of what the tool does and when to use it")
    input_schema: ToolInputSchema = Field(..., description="JSON Schema defining expected parameters")
    cache_control: CacheControl | None = None

    def with_cache(self) -> dict[str, Any]:
        """Return tool definition with caching enabled."""
        data = self.model_dump()
        data["cache_control"] = CacheControl().model_dump()
        return data

    def without_cache(self) -> dict[str, Any]:
        """Return tool definition without caching."""
        data = self.model_dump()
        data.pop("cache_control", None)
        return data


class SystemPrompt(BaseModel):
    """System prompt for LLM."""

    type: Literal["text"] = "text"
    text: str
    cache_control: CacheControl | None = None

    def with_cache(self) -> dict[str, Any]:
        """Return prompt with caching enabled."""
        data = self.model_dump()
        data["cache_control"] = CacheControl().model_dump()
        return data

    def without_cache(self) -> dict[str, Any]:
        """Return prompt without caching."""
        data = self.model_dump()
        data.pop("cache_control", None)
        return data
