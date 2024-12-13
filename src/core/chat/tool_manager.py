from pathlib import Path

import yaml
from pydantic import ValidationError

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings
from src.models.llm_models import Tool, ToolInputSchema

logger = get_logger()


class ToolManager:
    """Manage LLM tools following Anthropic's API spec."""

    def __init__(self, tools_dir: Path = settings.tools_dir, tools_file: str = settings.tools_file) -> None:
        self.tools_path = tools_dir / tools_file
        self.tools: dict[str, Tool] = {}
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

                self.tools[name] = Tool(**tool_data)

        except (yaml.YAMLError, ValidationError) as e:
            logger.error(f"Failed to load tools: {e}", exc_info=True)
            raise

    def get_all_tools(self) -> list[Tool]:
        """Get all tools with caching enabled."""
        return list(self.tools.values())

    def get_tool(self, name: str) -> Tool | None:
        """Get a specific tool by name."""
        return self.tools.get(name)