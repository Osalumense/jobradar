import os
import math
import asyncio
import logging
import google.generativeai as genai
from typing import List

logger = logging.getLogger("jobradar.embedder")

# Gemini free tier: 15 embedding requests/min → 1 per 4s is safe
# We use a simple semaphore + delay to stay under the limit
EMBED_DELAY_SECONDS = 1.5   # delay between calls
_embed_lock = asyncio.Lock()


class GeminiEmbedder:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.embedding_model = "models/gemini-embedding-001"
        self.embedding_dims = 3072  # gemini-embedding-001 output size

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured")

        genai.configure(api_key=self.api_key)

    async def get_embedding(self, text: str) -> List[float]:
        """Fetch vector embeddings from Gemini with rate-limit protection."""
        cleaned = text.replace("\n", " ").strip()
        if not cleaned:
            return [0.0] * self.embedding_dims

        # Throttle all embedding calls globally to avoid 429 quota errors
        async with _embed_lock:
            for attempt in range(1, 4):
                try:
                    response = genai.embed_content(
                        model=self.embedding_model,
                        content=cleaned[:8000],  # keep within token limits
                        task_type="retrieval_document"
                    )
                    embedding = response.get("embedding", [])
                    if embedding:
                        await asyncio.sleep(EMBED_DELAY_SECONDS)
                        return embedding
                    else:
                        logger.warning("Gemini returned empty embedding, retrying...")
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(e):
                        wait = attempt * 4.0
                        logger.warning(f"Gemini rate limit hit (attempt {attempt}), waiting {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Gemini embedding error (attempt {attempt}): {e}")
                        await asyncio.sleep(1.0)

        logger.error("All Gemini embedding attempts failed, returning zero vector")
        return [0.0] * self.embedding_dims

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))

        if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
            return 0.0

        return dot_product / (magnitude_v1 * magnitude_v2)
