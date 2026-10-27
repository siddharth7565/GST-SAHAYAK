"""Check which LLM providers work: sends 'Reply with OK' to each configured provider.

Run from the backend folder (venv active):
    python scripts/check_providers.py
    python scripts/check_providers.py gemini mistral

Prints provider, model, latency and success/error. API keys are never printed. A wrong model ID shows up
here as an error; fix it in backend/.env (GEMINI_MODEL, MISTRAL_MODEL, XAI_MODEL, OLLAMA_MODEL,
ANTHROPIC_MODEL, OPENAI_MODEL, DEEPSEEK_MODEL) without touching the code.
"""
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

from services.llm_providers import get_llm_provider  # noqa: E402

DEFAULT = ["gemini", "mistral", "grok", "ollama", "claude", "openai", "deepseek-api"]


def main():
    names = sys.argv[1:] or DEFAULT
    print(f"{'provider':<14}{'model':<28}{'status':<16}{'seconds':<9}detail")
    for name in names:
        try:
            p = get_llm_provider(name)
        except Exception as exc:
            print(f"{name:<14}{'-':<28}{'ERROR':<16}{'-':<9}{exc}")
            continue
        model = getattr(p, "_model_name", "-")
        if not p.is_configured():
            print(f"{name:<14}{model:<28}{'not configured':<16}{'-':<9}")
            continue
        start = time.time()
        try:
            reply = p.generate_response("Reply with OK")
            print(f"{name:<14}{model:<28}{'OK':<16}{time.time() - start:<9.2f}{(reply or '').strip()[:40]!r}")
        except Exception as exc:
            msg = str(exc).replace("\n", " ")[:160]
            print(f"{name:<14}{model:<28}{'FAILED':<16}{time.time() - start:<9.2f}{msg}")


if __name__ == "__main__":
    main()
