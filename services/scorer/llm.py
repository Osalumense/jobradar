from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Asynchronously generate text based on prompts."""
        pass
