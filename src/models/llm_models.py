from enum import Enum
from typing import Any, Literal

from anthropic.types.text_block_param import TextBlockParam
from anthropic.types.tool_param import ToolParam
from pydantic import BaseModel, Field


class CacheControl(BaseModel):
    """Cache control for Anthropic API."""

    type: Literal["ephemeral"] = "ephemeral"


class ToolInputSchema(BaseModel):
    """Base model for tool input schema validation."""

    type: Literal["object"] = "object"
    properties: dict[str, Any]
    required: list[str] | None = None


class ToolName(str, Enum):
    """Tool names."""

    RAG_SEARCH = "rag_search"
    MULTI_QUERY = "multi_query_tool"
    SUMMARY = "summary_tool"


class Tool(BaseModel):
    """Tool definition for LLM following Anthropic's API spec."""

    name: ToolName = Field(..., description="Tool name. Must match regex ^[a-zA-Z0-9_-]{1,64}$")
    description: str = Field(..., description="Detailed description of what the tool does and when to use it")
    input_schema: ToolInputSchema = Field(..., description="JSON Schema defining expected parameters")
    cache_control: CacheControl | None = None

    @classmethod
    def from_tool_param(cls, tool_param: ToolParam) -> "Tool":
        """Convert Anthropic's ToolParam to our Tool model."""
        return cls(
            name=ToolName(tool_param["name"]),
            description=tool_param["description"],
            input_schema=tool_param["input_schema"],
        )

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


class PromptType(str, Enum):
    """Enum for prompt types for PromptManager."""

    LLM_ASSISTANT_PROMPT = "llm_assistant_prompt"  # Used for the LLM assistant
    MULTI_QUERY_PROMPT = "multi_query_prompt"  # Used for the multi-query prompt
    SUMMARY_PROMPT = "summary_prompt"  # Used for the summary prompt


class SystemPrompt(BaseModel):
    """System prompt model for Anthropic LLMs."""

    type: Literal["text"] = "text"
    text: str
    cache_control: CacheControl | None = None

    def with_cache(self) -> TextBlockParam:
        """Return prompt with caching enabled."""
        data = self.model_dump()
        data["cache_control"] = CacheControl().model_dump()
        return data

    def without_cache(self) -> dict[str, Any]:
        """Return prompt without caching."""
        data = self.model_dump()
        data.pop("cache_control", None)
        return data
