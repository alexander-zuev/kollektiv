from pathlib import Path
from typing import Any

import yaml

from src.infra.settings import settings
from src.models.llm_models import PromptType, SystemPrompt


class PromptManager:
    """Manages loading and formatting of system prompts."""

    def __init__(self, prompt_dir: Path = settings.prompt_dir, prompt_file: str = settings.prompts_file):
        self.prompt_path = prompt_dir / prompt_file
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load prompts from YAML file."""
        with open(self.prompt_path) as f:
            self.prompts = yaml.safe_load(f)

    # TODO: Refactor to be prompt-agnostic
    def get_system_prompt(self, **kwargs: Any) -> SystemPrompt:
        """Get system prompt model with provided kwargs."""
        text = self.prompts[PromptType.LLM_ASSISTANT_PROMPT].format(**kwargs)
        return SystemPrompt(text=text)

    def get_multi_query_prompt(self, **kwargs: Any) -> str:
        """Get multi-query prompt."""
        try:
            text = self.prompts[PromptType.MULTI_QUERY_PROMPT].format(**kwargs)
        except KeyError:
            raise ValueError("Multi-query prompt not found")
        if isinstance(text, str):
            return text
        raise ValueError("Multi-query prompt is not a string")

    def get_summary_prompt(self, **kwargs: Any) -> str:
        """Get summary prompt."""
        try:
            text = self.prompts[PromptType.SUMMARY_PROMPT].format(**kwargs)
        except KeyError:
            raise ValueError("Summary prompt not found")
        return text

    def return_system_prompt(self, prompt_type: PromptType, **kwargs: Any) -> SystemPrompt:
        """Return a prompt-agnostic system prompt."""
        try:
            text = self.prompts[prompt_type].format(**kwargs)
        except KeyError as e:
            raise ValueError(f"System prompt not found for {prompt_type}") from e
        return SystemPrompt(text=text)
