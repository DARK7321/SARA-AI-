"""Prompt Registry for OmniBrain.

Versioned prompts stored as YAML files to ensure prompts are never hardcoded inline.
"""
import os
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel


class PromptTemplate(BaseModel):
    key: str
    version: int = 1
    system_prompt: Optional[str] = None
    user_template: str
    model_tier: str = "fast"
    description: Optional[str] = None


class PromptRegistry:
    """Loads and formats versioned prompts from the prompts/ directory."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.cache: Dict[str, PromptTemplate] = {}

    def get(self, key: str, version: int = 1) -> PromptTemplate:
        """Load a prompt template by key and version."""
        cache_key = f"{key}@v{version}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        file_name = f"{key}@v{version}.yaml"
        file_path = os.path.join(self.prompts_dir, file_name)

        if not os.path.exists(file_path):
            # Fallback to general template
            return PromptTemplate(
                key=key,
                version=version,
                user_template="{input}",
            )

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        template = PromptTemplate(
            key=key,
            version=version,
            system_prompt=data.get("system_prompt"),
            user_template=data.get("user_template", "{input}"),
            model_tier=data.get("model_tier", "fast"),
            description=data.get("description"),
        )
        self.cache[cache_key] = template
        return template

    def format(self, key: str, version: int = 1, **kwargs: Any) -> tuple[Optional[str], str]:
        """Format the prompt template with provided keyword arguments.
        
        Returns:
            (system_prompt, formatted_user_prompt)
        """
        template = self.get(key, version)
        formatted_user = template.user_template.format(**kwargs)
        return template.system_prompt, formatted_user

