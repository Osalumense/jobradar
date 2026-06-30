import os
from llm import LLMProvider
import google.generativeai as genai

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        # Load model dynamically from environment variables, defaulting to gemini-2.5-pro
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured")
            
        genai.configure(api_key=self.api_key)

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Asynchronously call Gemini API to generate text content."""
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        response = await model.generate_content_async(prompt)
        return response.text
