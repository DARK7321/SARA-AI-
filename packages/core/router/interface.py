"""Model Router Provider Interface for OmniBrain.

Abstracts multi-vendor LLM access behind a unified contract with
token tracking, latency tracking, structured output validation, and cost logging.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field


class ModelResponse(BaseModel):
    """Unified response envelope for all LLM calls."""
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0.000000")
    latency_ms: int = 0
    provider: str


class BaseModelProvider(ABC):
    """Abstract base class for all LLM provider adapters."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        """Generate a response, optionally parsed into a Pydantic schema."""
        ...

