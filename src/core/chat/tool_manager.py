from pathlib import Path

import yaml
from anthropic.types import ToolChoiceToolParam, ToolParam
from pydantic import ValidationError

from src.core._exceptions import NonRetryableLLMError
from src.infra.logger import get_logger
from src.infra.settings import settings
from src.models.llm_models import Tool, ToolInputSchema, ToolName

logger = get_logger()


class ToolManager:
    """Manage LLM tools following Anthropic's API spec."""

    def __init__(self, tools_dir: Path = settings.tools_dir, tools_file: str = settings.tools_file) -> None:
        self.tools_path = tools_dir / tools_file
        self.tools: dict[ToolName, Tool] = {}
        self._load_tools()

    def _load_tools(self) -> None:
        """Load and validate tools from YAML file."""
        try:
            with open(self.tools_path) as f:
                raw_tools = yaml.safe_load(f)

            for name, tool_data in raw_tools.items():
                # Ensure input_schema is properly structured
                if "input_schema" in tool_data:
                    tool_data["input_schema"] = ToolInputSchema(**tool_data["input_schema"])

                # Convert string name to ToolName enum
                tool_name = ToolName(name)  # This validates the name matches an enum value
                self.tools[tool_name] = Tool(**tool_data)

        except (yaml.YAMLError, ValidationError) as e:
            logger.error(f"Failed to load tools: {e}", exc_info=True)
            raise

    def get_all_tools(self) -> list[Tool]:
        """Get all tools with caching enabled."""
        return list(self.tools.values())

    def get_tool(self, name: ToolName) -> ToolParam:
        """Get a specific tool by name."""
        try:
            tool = self.tools.get(name)
            if not tool:
                raise KeyError(f"Tool {name} not found")
            return ToolParam(name=tool.name, input_schema=tool.input_schema, description=tool.description)
        except KeyError as e:
            logger.error(f"Tool {name} not found")
            raise NonRetryableLLMError(original_error=e, message=f"Tool {name} not found") from e

    def force_tool_choice(self, name: ToolName) -> ToolChoiceToolParam:
        """Forces Claude to always use the tool."""
        return ToolChoiceToolParam(type="tool", name=name.value)


if __name__ == "__main__":
    # Initialize manager
    manager = ToolManager()

    # Test tool retrieval and conversion
    rag_tool = manager.get_tool(ToolName.RAG_SEARCH)
    # print(f"RAG tool: {rag_tool}")

    my_tool = Tool.from_tool_param(rag_tool)
    print(f"My tool: {my_tool}")

    # Test tool choice
    tool_choice = manager.force_tool_choice(ToolName.RAG_SEARCH)
    print(f"Tool choice: {tool_choice}")
