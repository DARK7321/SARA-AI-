"""Google Gemini Provider Adapter for OmniBrain.

Supports Gemini 2.0 Flash and Gemini 2.5 Pro via google-generativeai.
"""
import json
import time
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, Optional, Type
from pydantic import BaseModel

import google.generativeai as genai

from apps.api.settings import get_settings
from packages.core.router.interface import BaseModelProvider, ModelResponse


class GeminiProvider(BaseModelProvider):
    """Google Gemini adapter with structured outputs and token tracking."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="gemini")
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> ModelResponse:
        """Call Gemini API and return standardized ModelResponse."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please provide an API key in .env"
            )

        model_id = model_name or "gemini-3.5-flash-lite"
        start_time = time.time()

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # If schema requested, instruct model to output strictly valid JSON
        enhanced_prompt = prompt
        if schema:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            enhanced_prompt = (
                f"{prompt}\n\n"
                f"You MUST respond ONLY with a valid JSON object strictly conforming to this JSON Schema:\n"
                f"```json\n{schema_json}\n```\n"
                f"Do not include explanations or markdown formatting outside the JSON."
            )
            generation_config.response_mime_type = "application/json"

        model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=generation_config,
        )

        response = await model.generate_content_async(enhanced_prompt)
        latency_ms = int((time.time() - start_time) * 1000)

        raw_text = response.text.strip()
        structured_dict: Optional[Dict[str, Any]] = None

        if schema:
            # Clean possible markdown fences if returned
            clean_text = raw_text
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            validated_obj = schema.model_validate_json(clean_text)
            structured_dict = validated_obj.model_dump()

        # Token usage extraction
        tokens_in = 0
        tokens_out = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        # Cost calculation (Gemini 2.0 Flash is effectively $0 in free tier)
        cost_usd = Decimal("0.000000")

        return ModelResponse(
            content=raw_text,
            structured_data=structured_dict,
            model=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider="gemini",
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        """Stream response tokens from Gemini API in real-time."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        model_id = model_name or "gemini-3.5-flash-lite"

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=system_prompt if system_prompt else None,
            generation_config=generation_config,
        )

        response = await model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text


