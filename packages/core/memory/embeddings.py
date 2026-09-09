"""Embedding Engine for OmniBrain Long-Term Memory.

Uses Google Gemini text-embedding-004 (768-dim) when configured,
with a deterministic semantic hashing fallback for offline sandbox testing.
"""
import hashlib
import logging
import math
from typing import List, Optional

from apps.api.settings import get_settings

logger = logging.getLogger("omnibrain.memory.embeddings")

EMBEDDING_DIM = 768


def compute_fallback_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Generate a deterministic 768-dim normalized embedding vector.
    
    Uses token hashing and character n-grams to preserve lexical similarity
    in offline development and automated test suites without external API calls.
    """
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    words = text.lower().strip().split()

    for word in words:
        # Full word hash
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.5
        
        # Word bigrams
        for i in range(len(word) - 1):
            bg = word[i : i + 2]
            h_bg = int(hashlib.sha256(bg.encode("utf-8")).hexdigest(), 16)
            vec[h_bg % dim] += 0.5

    # Normalize to unit vector for cosine distance
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        return [x / norm for x in vec]
    return vec


class EmbeddingService:
    """Service to produce 768-dimensional embeddings for texts."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.is_configured = bool(
            self.api_key and self.api_key != "your-gemini-api-key"
        )
        if self.is_configured:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not configure genai for embeddings: {e}")
                self.is_configured = False

    async def get_embedding(self, text: str) -> List[float]:
        """Generate a 768-dimensional embedding for text."""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        if self.is_configured:
            try:
                import google.generativeai as genai
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document",
                )
                if "embedding" in result and result["embedding"]:
                    return result["embedding"]
            except Exception as e:
                logger.warning(f"Gemini embed_content failed, using fallback: {e}")

        return compute_fallback_embedding(text, dim=EMBEDDING_DIM)


_default_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Singleton getter for EmbeddingService."""
    global _default_embedding_service
    if _default_embedding_service is None:
        _default_embedding_service = EmbeddingService()
    return _default_embedding_service

