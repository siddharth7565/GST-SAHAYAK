from typing import Optional
from services.llm_providers import get_llm_provider, BaseLLMProvider


class LLMService:
    """
    Production LLM Service wrapper for GST Sahayak.
    Delegates text generation to the configured LLMProvider via provider_factory.
    Preserves existing generate_response() contract for RAGService and main.py endpoints.
    """

    def __init__(self, default_provider_name: Optional[str] = None):
        self._default_provider_name = default_provider_name

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Returns requested provider or default configured provider."""
        target = provider_name or self._default_provider_name
        return get_llm_provider(target)

    def generate_response(self, prompt: str, provider_name: Optional[str] = None) -> str:
        """
        Generates text response using active LLMProvider.
        """
        provider = self.get_provider(provider_name)
        return provider.generate_response(prompt)


# Global singleton instance of LLMService (uses env default, Gemini)
llm_service = LLMService()
