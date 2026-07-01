import re
from typing import List, Tuple

class KeywordMatcher:
    @staticmethod
    def clean_text(text: str) -> str:
        """Lowercase and remove non-alphanumeric characters for clean tokenization."""
        return re.sub(r'[^\w\s]', '', text.lower())

    def calculate_score(self, text: str, keywords: List[str], excluded: List[str]) -> Tuple[float, List[str]]:
        """
        Calculate a keyword match ratio (0-1).
        
        Returns:
            - score (float): ratio of matched keywords
            - matched_words (List[str]): list of matching keywords found in text
        """
        cleaned_text = self.clean_text(text)

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
