from datetime import datetime, timezone
import math
from typing import Dict, Any, List
from embedder import GeminiEmbedder
from keyword_matcher import KeywordMatcher

WEIGHTS = {
    "semantic": 0.55,
    "keyword": 0.30,
    "recency": 0.15,
}

class CompositeScorer:
    def __init__(self, embedder: GeminiEmbedder, matcher: KeywordMatcher):
        self.embedder = embedder
        self.matcher = matcher

    def calculate_recency(self, posted_at: datetime | None) -> float:
        """Exponential decay: 1.0 today, ~0.5 at 7 days, ~0.05 at 30 days."""
        if posted_at is None:
            return 0.5  # Neutral fallback for unknown dates
            
        # Ensure UTC timezone
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        age_days = (now - posted_at).total_seconds() / 86400.0
        
        # Avoid negative age due to clock drift
        age_days = max(0.0, age_days)
        return math.exp(-0.1 * age_days)

    async def score_job(
        self, 
        description: str, 
        posted_at: datetime | None, 
        profile_text: str, 
        profile_embedding: List[float],
        keywords: List[str], 
        excluded: List[str]
    ) -> Dict[str, Any]:
        """Compute the final composite matching score."""
        
        # 1. Keyword check & Exclusions (Fast fail)
        keyword_score, matched_words = self.matcher.calculate_score(description, keywords, excluded)
        
        # If the job contains exclusion criteria, score is automatically 0
        if keyword_score == 0.0 and len(excluded) > 0:
            return {
                "semantic": 0.0,
                "keyword": 0.0,
                "recency": 0.0,
                "composite": 0.0,
                "tech_stack": matched_words
            }

        # 2. Semantic matching via Gemini Embeddings API
        job_embedding = await self.embedder.get_embedding(description)
        semantic_score = self.embedder.cosine_similarity(profile_embedding, job_embedding)
        
        # Normalize semantic score range (shifting negative bounds if any)
        semantic_score = max(0.0, min(1.0, semantic_score))

        # 3. Recency decay calculation
        recency = self.calculate_recency(posted_at)

        # 4. Weighted Composite Score
        composite = (
            semantic_score * WEIGHTS["semantic"] +
            keyword_score * WEIGHTS["keyword"] +
            recency * WEIGHTS["recency"]
        )

        return {
            "semantic": round(semantic_score, 4),
            "keyword": round(keyword_score, 4),
            "recency": round(recency, 4),
            "composite": round(composite, 4),
            "tech_stack": matched_words
        }
