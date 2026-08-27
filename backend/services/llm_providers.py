from abc import ABC, abstractmethod
import os
import json
import urllib.request
import urllib.error
import socket
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers (Gemini, OpenAI, Claude, Ollama).
    Defines common interface for generating responses and checking configuration status.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical name of the LLM provider."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required API key or server connection is configured."""
        pass

    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """Generates text response for the given prompt using the provider's API."""
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider implementation using official google-genai SDK.
    Primary/default model: gemini-3.6-flash.
    """

    def __init__(self, model_name: str = "gemini-3.6-flash"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        api_key = os.getenv("GEMINI_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if not self.is_configured():
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env.")

        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)

        # Primary active model: gemini-3.6-flash.
        candidate_models = [self._model_name, "gemini-3.6-flash"]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        for model in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt.strip()
                )
                if response and response.text:
                    return response.text
            except Exception as exc:
                last_error = exc
                if "404" in str(exc) or "NOT_FOUND" in str(exc):
                    continue
                raise RuntimeError(f"Gemini API call failed: {str(exc)}")

        raise RuntimeError(f"Gemini API call failed for models {candidate_models}: {str(last_error)}")


class OllamaProvider(BaseLLMProvider):
    """
    Remote Ollama Cloud API provider implementation using REST API.
    Connects to https://ollama.com/api/chat using OLLAMA_API_KEY from backend/.env.
    Does NOT use localhost:11434 or local ollama serve.
    """

    def __init__(self, model_name: str = "gpt-oss:20b", api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._model_name = model_name
        self._api_key = api_key or os.getenv("OLLAMA_API_KEY")
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "https://ollama.com")).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_configured(self) -> bool:
        api_key = self._api_key or os.getenv("OLLAMA_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        api_key = self._api_key or os.getenv("OLLAMA_API_KEY")
        if not self.is_configured() or not api_key:
            raise RuntimeError("Ollama API key (OLLAMA_API_KEY) is not configured. Please set OLLAMA_API_KEY in backend/.env.")

        url = "https://ollama.com/api/chat" if "localhost" in self._base_url else f"{self._base_url}/api/chat"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "stream": False
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API returned HTTP {response.status}")
                res_data = json.loads(response.read().decode("utf-8"))
                message = res_data.get("message", {})
                ans_text = message.get("content", "")
                if not ans_text or not ans_text.strip():
                    ans_text = res_data.get("response", "") or f"Ollama model '{self._model_name}' execution completed."
                return ans_text.strip()
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 401:
                raise RuntimeError("Ollama API error 401: Invalid API Key.")
            elif exc.code == 403:
                raise RuntimeError("Ollama API error 403: Permission denied / Access forbidden.")
            elif exc.code == 402:
                raise RuntimeError("Ollama API error 402: Quota or billing error on Ollama Cloud account.")
            elif exc.code == 429:
                raise RuntimeError("Ollama API error 429: Rate limit exceeded.")
            else:
                raise RuntimeError(f"Ollama HTTP error {exc.code}: {exc.reason} - {err_body[:100]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama API unreachable at {url}: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise RuntimeError(f"Ollama API request timed out after 60s at {url}.")
        except Exception as exc:
            raise RuntimeError(f"Ollama API call failed: {str(exc)}")


class DeepSeekLocalProvider(OllamaProvider):
    """
    Local DeepSeek-R1 7B LLM provider implementation running via local Ollama REST service.
    Connects to http://localhost:11434 with model 'deepseek-r1:7b'.
    No API key required.
    """

    def __init__(self, model_name: str = "deepseek-r1:7b", base_url: Optional[str] = None):
        super().__init__(model_name=model_name, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return "deepseek-local"


class DeepSeekProvider(BaseLLMProvider):
    """
    Official DeepSeek API provider implementation using REST API.
    Connects to https://api.deepseek.com/chat/completions using DEEPSEEK_API_KEY.
    """

    def __init__(self, model_name: str = "deepseek-v4-flash", api_key: Optional[str] = None):
        self._model_name = model_name
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = "https://api.deepseek.com"

    @property
    def provider_name(self) -> str:
        return "deepseek"

    def is_configured(self) -> bool:
        api_key = self._api_key or os.getenv("DEEPSEEK_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        api_key = self._api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.is_configured() or not api_key:
            raise RuntimeError("DeepSeek API key (DEEPSEEK_API_KEY) is not configured. Please set DEEPSEEK_API_KEY in backend/.env.")

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "stream": False
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"DeepSeek API returned HTTP {response.status}")
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if not choices or not choices[0].get("message", {}).get("content"):
                    raise RuntimeError(f"DeepSeek API returned empty response for model '{self._model_name}'.")
                return choices[0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 402:
                raise RuntimeError("DeepSeek API error 402: Insufficient Balance / Quota Exhausted on DeepSeek account.")
            elif exc.code == 401:
                raise RuntimeError("DeepSeek API error 401: Invalid API Key.")
            elif exc.code == 429:
                raise RuntimeError("DeepSeek API error 429: Rate Limit Exceeded.")
            else:
                raise RuntimeError(f"DeepSeek HTTP error {exc.code}: {exc.reason} - {err_body[:100]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek API unreachable at {self._base_url}: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise RuntimeError(f"DeepSeek API request timed out after 60s at {self._base_url}.")
        except Exception as exc:
            raise RuntimeError(f"DeepSeek API call failed: {str(exc)}")


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT-4 LLM provider implementation using official openai SDK.
    Handles missing keys cleanly without crashing application startup.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        api_key = os.getenv("OPENAI_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if not self.is_configured():
            raise RuntimeError("OpenAI API key (OPENAI_API_KEY) is not configured. Please set OPENAI_API_KEY in backend/.env.")

        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt.strip()}]
            )
            return response.choices[0].message.content
        except Exception as exc:
            if "OPENAI_API_KEY" in str(exc) or "Prompt cannot be empty" in str(exc):
                raise exc
            raise RuntimeError(f"OpenAI API call failed: {str(exc)}")


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude LLM provider implementation using official anthropic SDK.
    Handles missing keys cleanly without crashing application startup.
    """

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "claude"

    def is_configured(self) -> bool:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if not self.is_configured():
            raise RuntimeError("Anthropic Claude API key (ANTHROPIC_API_KEY) is not configured. Please set ANTHROPIC_API_KEY in backend/.env.")

        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=self._model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt.strip()}]
            )
            return response.content[0].text
        except Exception as exc:
            if "ANTHROPIC_API_KEY" in str(exc) or "Prompt cannot be empty" in str(exc):
                raise exc
            raise RuntimeError(f"Claude API call failed: {str(exc)}")


class MistralProvider(BaseLLMProvider):
    """
    Official Mistral API provider implementation using REST API.
    Connects to https://api.mistral.ai/v1/chat/completions using MISTRAL_API_KEY.
    """

    def __init__(self, model_name: str = "mistral-small-latest", api_key: Optional[str] = None):
        self._model_name = model_name
        self._api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self._base_url = "https://api.mistral.ai"

    @property
    def provider_name(self) -> str:
        return "mistral"

    def is_configured(self) -> bool:
        api_key = self._api_key or os.getenv("MISTRAL_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        api_key = self._api_key or os.getenv("MISTRAL_API_KEY")
        if not self.is_configured() or not api_key:
            raise RuntimeError("Mistral API key (MISTRAL_API_KEY) is not configured. Please set MISTRAL_API_KEY in backend/.env.")

        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "stream": False
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"Mistral API returned HTTP {response.status}")
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if not choices or not choices[0].get("message", {}).get("content"):
                    raise RuntimeError(f"Mistral API returned empty response for model '{self._model_name}'.")
                return choices[0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 401:
                raise RuntimeError("Mistral API error 401: Invalid API Key.")
            elif exc.code == 429:
                raise RuntimeError("Mistral API error 429: Rate Limit Exceeded.")
            else:
                raise RuntimeError(f"Mistral HTTP error {exc.code}: {exc.reason} - {err_body[:100]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Mistral API unreachable at {self._base_url}: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise RuntimeError(f"Mistral API request timed out after 60s at {self._base_url}.")
        except Exception as exc:
            raise RuntimeError(f"Mistral API call failed: {str(exc)}")


class GrokProvider(BaseLLMProvider):
    """
    Official xAI Grok LLM provider implementation using REST API.
    Connects to https://api.x.ai/v1/chat/completions using XAI_API_KEY.
    Primary active model: grok-4.6.
    """

    def __init__(self, model_name: str = "grok-4.6", api_key: Optional[str] = None):
        self._model_name = model_name
        self._api_key = api_key or os.getenv("XAI_API_KEY")
        self._base_url = "https://api.x.ai/v1"

    @property
    def provider_name(self) -> str:
        return "grok"

    def is_configured(self) -> bool:
        api_key = self._api_key or os.getenv("XAI_API_KEY")
        return bool(api_key and len(api_key.strip()) > 10 and not api_key.startswith("your_") and not api_key.startswith("YOUR_"))

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        api_key = self._api_key or os.getenv("XAI_API_KEY")
        if not self.is_configured() or not api_key:
            raise RuntimeError("xAI Grok API key (XAI_API_KEY) is not configured. Please set XAI_API_KEY in backend/.env.")

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "stream": False
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"Grok API returned HTTP {response.status}")
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"].strip()
                elif res_data.get("output"):
                    return str(res_data["output"]).strip()
                else:
                    raise RuntimeError(f"Grok API returned empty response for model '{self._model_name}'.")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 401:
                raise RuntimeError(f"Grok API error 401: Invalid API Key / Bad credentials. Details: {err_body[:100]}")
            elif exc.code == 403:
                raise RuntimeError(f"Grok API error 403: Permission denied. Details: {err_body[:100]}")
            elif exc.code == 402:
                raise RuntimeError(f"Grok API error 402: Quota or billing limit exceeded. Details: {err_body[:100]}")
            elif exc.code == 429:
                raise RuntimeError(f"Grok API error 429: Rate Limit Exceeded. Details: {err_body[:100]}")
            else:
                raise RuntimeError(f"Grok HTTP error {exc.code}: {exc.reason} - {err_body[:100]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Grok API unreachable at {self._base_url}: {exc.reason}")
        except (TimeoutError, socket.timeout):
            raise RuntimeError(f"Grok API request timed out after 60s at {self._base_url}.")
        except Exception as exc:
            raise RuntimeError(f"Grok API call failed: {str(exc)}")


class LLMProviderFactory:
    """
    Factory class for registry and selection of LLM providers.
    """

    def __init__(self):
        self._providers = {
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "qwen": OllamaProvider(),
            "mistral": MistralProvider(),
            "mistral-api": MistralProvider(),
            "grok": GrokProvider(),
            "grok-api": GrokProvider(),
            "deepseek": DeepSeekLocalProvider(),
            "deepseek-local": DeepSeekLocalProvider(),
            "deepseek-r1": DeepSeekLocalProvider(),
            "deepseek-api": DeepSeekProvider(),
            "openai": OpenAIProvider(),
            "claude": ClaudeProvider(),
            "anthropic": ClaudeProvider()
        }

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """
        Returns requested provider or defaults to LLM_PROVIDER env variable / 'gemini'.
        """
        selected_name = name or os.getenv("LLM_PROVIDER", "gemini")
        clean_name = selected_name.strip().lower()

        if clean_name not in self._providers:
            supported = ", ".join(sorted(list(set(self._providers.keys()))))
            raise ValueError(f"Unsupported LLM provider '{name}'. Supported providers: {supported}")

        return self._providers[clean_name]


# Global provider factory instance
provider_factory = LLMProviderFactory()


def get_llm_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """Convenience helper to retrieve an LLM provider instance by name."""
    return provider_factory.get_provider(name)
