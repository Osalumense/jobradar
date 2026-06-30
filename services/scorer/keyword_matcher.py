import re
from typing import List, Set, Tuple

class KeywordMatcher:
    @staticmethod
    def clean_text(text: str) -> str:
        """Lowercase and remove non-alphanumeric characters for clean tokenization."""
        return re.sub(r'[^\w\s]', '', text.lower())

    def calculate_score(self, text: str, keywords: List[str], excluded: List[str]) -> Tuple[float, List[str]]:
        """
        Calculate a keyword match ratio (0-1) and check for exclusion criteria.
        
        Returns:
            - score (float): ratio of matched keywords (0.0 if excluded keywords found)
            - matched_words (List[str]): list of matching keywords found in text
        """
        cleaned_text = self.clean_text(text)
        text_tokens = set(cleaned_text.split())
        
        # 1. Exclusion Check (strict check)
        # Check if any exclusion phrases appear in the raw lowercase description
        desc_lower = text.lower()
        for exc in excluded:
            exc_clean = exc.lower().strip()
            if not exc_clean:
                continue
            # Use regex word boundaries or substring match for safety
            if exc_clean in desc_lower:
                return 0.0, []

        # 2. Match Keywords
        matched = []
        if not keywords:
            return 1.0, []

        for kw in keywords:
            kw_clean = kw.lower().strip()
            if not kw_clean:
                continue
            
            # Simple substring word boundary check
            pattern = r'\b' + re.escape(kw_clean) + r'\b'
            if re.search(pattern, cleaned_text):
                matched.append(kw_clean)
                
        score = len(matched) / len(keywords)
        return round(score, 4), matched
