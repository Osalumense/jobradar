import os
import math
import google.generativeai as genai
from typing import List

class GeminiEmbedder:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.embedding_model = "models/text-embedding-004"
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured")
            
        genai.configure(api_key=self.api_key)

    async def get_embedding(self, text: str) -> List[float]:
        """Fetch vector embeddings from Google Gemini API."""
        # Clean text slightly to fit embedding requirements
        cleaned_text = text.replace("\n", " ").strip()
        if not cleaned_text:
            return [0.0] * 768  # text-embedding-004 has 768 dimensions

        # Run async in executor if the SDK call is blocking
        # google-generativeai offers embed_content; we wrap it defensively
        response = genai.embed_content(
            model=self.embedding_model,
            contents=cleaned_text,
            task_type="retrieval_document"
        )
        return response.get("embedding", [])

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity in pure Python (no numpy dependency required)."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        
        if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
            return 0.0
            
        return dot_product / (magnitude_v1 * magnitude_v2)
