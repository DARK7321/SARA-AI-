"""Model Router package for OmniBrain."""
from .interface import BaseModelProvider, ModelResponse
from .model_router import ModelRouter
from .prompt_registry import PromptRegistry, PromptTemplate
from .providers.gemini import GeminiProvider
from .providers.mock import MockModelProvider

__all__ = [
    "BaseModelProvider",
    "ModelResponse",
    "ModelRouter",
    "PromptRegistry",
    "PromptTemplate",
    "GeminiProvider",
    "MockModelProvider",
]

