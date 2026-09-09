"""Model Router for OmniBrain.

Handles dynamic routing across model tiers (FAST / SMART / DEEP) and providers.
"""
from decimal import Decimal
import os
from typing import Any, Dict, Optional, Type
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import yaml

from packages.core.router.interface import BaseModelProvider, ModelResponse
from packages.core.router.providers.gemini import GeminiProvider
from packages.core.router.providers.mock import MockModelProvider
from packages.core.db.models import PromptRun


class ModelRouter:
    """Selects the optimal model tier based on task path and complexity."""

    def __init__(self, config_path: str = "config/models.yaml"):
        self.config_path = config_path
        self.providers: Dict[str, BaseModelProvider] = {}
        self.task_routing: Dict[str, str] = {
            "FAST": "gemini-2.0-flash",
            "SMART": "gemini-2.0-flash",
            "DEEP": "gemini-2.5-pro",
        }
        self._initialize()

    def _initialize(self) -> None:
        """Register default providers and load routing config."""
        # Always register providers
        self.providers["gemini"] = GeminiProvider()
        self.providers["mock"] = MockModelProvider()

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    routing = data.get("task_routing", {})
                    # Map config values to model IDs
                    for path, target in routing.items():
                        if "flash" in target:
                            self.task_routing[path] = "gemini-2.0-flash"
                        elif "pro" in target:
                            self.task_routing[path] = "gemini-2.5-pro"
            except Exception:
                pass

    def get_provider(self, provider_name: str = "gemini") -> BaseModelProvider:
        """Retrieve configured provider by name."""
        return self.providers.get(provider_name, self.providers["gemini"])

    async def complete(
        self,
        prompt: str,
        path: str = "SMART",
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        provider_name: str = "gemini",
        db_session: Optional[AsyncSession] = None,
        prompt_key: Optional[str] = None,
        prompt_version: int = 1,
        task_step_id: Optional[UUID] = None,
    ) -> ModelResponse:
        provider = self.get_provider(provider_name)
        model_id = self.task_routing.get(path, "gemini-2.0-flash")

        # Check if Gemini key is placeholder or missing
        gemini_prov = self.providers.get("gemini")
        if provider_name == "gemini" and gemini_prov and (
            not getattr(gemini_prov, "api_key", None)
            or "your-gemini" in getattr(gemini_prov, "api_key", "")
        ):
            provider = self.get_provider("mock")

        try:
            response = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=schema,
                model_name=model_id,
            )
        except Exception:
            # Graceful fallback to mock provider if remote API call fails
            mock_provider = self.get_provider("mock")
            response = await mock_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=schema,
                model_name=model_id,
            )

        # Record telemetry in prompt_runs table if db session provided
        if db_session and prompt_key:
            run_record = PromptRun(
                prompt_key=prompt_key,
                version=prompt_version,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=response.cost_usd,
                latency_ms=response.latency_ms,
                task_step_id=task_step_id,
                valid_output=True,
            )
            db_session.add(run_record)
            await db_session.flush()

        return response

