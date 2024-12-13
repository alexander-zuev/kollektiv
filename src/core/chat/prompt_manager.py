from pathlib import Path
from typing import Any

import yaml

from src.infrastructure.config.settings import settings
from src.models.llm_models import SystemPrompt


class PromptManager:
    """Manages loading and formatting of system prompts."""

    def __init__(self, prompt_dir: Path = settings.prompt_dir, prompt_file: str = settings.prompts_file):
        self.prompt_path = prompt_dir / prompt_file
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load prompts from YAML file."""
        with open(self.prompt_path) as f:
            self.prompts = yaml.safe_load(f)

    def get_system_prompt(self, **kwargs: Any) -> SystemPrompt:
        """Get system prompt model with provided kwargs."""
        text = self.prompts["base_prompt"].format(**kwargs)
        return SystemPrompt(text=text)
