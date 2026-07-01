from datetime import datetime, timezone
import math
from typing import Dict, Any, List
from embedder import GeminiEmbedder
from keyword_matcher import KeywordMatcher

WEIGHTS = {
    "semantic": 0.45,
    "keyword": 0.40,
    "recency": 0.15,
}

PREFERENCE_MISMATCH_FACTOR = 0.75

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
        excluded: List[str],
        contract_type: str | None,
        location: str | None,
        target_contracts: List[str],
        target_locations: List[str]
    ) -> Dict[str, Any]:
        """Compute a final composite score without hiding imperfect matches."""
        preference_factor = 1.0

        if target_contracts and contract_type:
            job_contract = contract_type.lower().strip()
            if not any(tc.lower().strip() in job_contract for tc in target_contracts):
                preference_factor *= PREFERENCE_MISMATCH_FACTOR

        if target_locations and location:
            job_loc = location.lower().strip()
            matched_loc = False
            for tl in target_locations:
                tl_clean = tl.lower().strip()
                if tl_clean in job_loc:
                    matched_loc = True
                    break
            if not matched_loc:
                preference_factor *= PREFERENCE_MISMATCH_FACTOR

        keyword_score, matched_words = self.matcher.calculate_score(description, keywords, excluded)

        job_embedding = await self.embedder.get_embedding(description)
        semantic_score = self.embedder.cosine_similarity(profile_embedding, job_embedding)
        semantic_score = max(0.0, min(1.0, semantic_score))

        recency = self.calculate_recency(posted_at)

        composite = (
            semantic_score * WEIGHTS["semantic"] +
            keyword_score * WEIGHTS["keyword"] +
            recency * WEIGHTS["recency"]
        ) * preference_factor

        return {
            "semantic": round(semantic_score, 4),
            "keyword": round(keyword_score, 4),
            "recency": round(recency, 4),
            "composite": round(composite, 4),
            "tech_stack": matched_words
        }
