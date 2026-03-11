"""
Ollama API client for GUNA-ASTRA.
All agents use this to communicate with Llama3.
"""

import requests
import json
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
from utils.logger import get_logger

logger = get_logger("OllamaClient")


def query_llm(prompt: str, system_prompt: str = "", model: str = OLLAMA_MODEL) -> str:
    """
    Send a prompt to Ollama and return the response text.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`")
        return "ERROR: Ollama is not running. Please start it with `ollama serve`."
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out.")
        return "ERROR: Request timed out."
    except Exception as e:
        logger.error(f"LLM query failed: {e}")
        return f"ERROR: {str(e)}"


def check_ollama_health() -> bool:
    """Check if Ollama is reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ─── v2 LLMClient Class ─────────────────────────────────────────────────────

class LLMClient:
    """v2-style LLM client with object-oriented interface."""

    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def ask(self, user: str, system: str = "", temperature: float = 0.7,
            max_tokens: int = 2000) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat",
                              json=payload, timeout=OLLAMA_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Ollama is not running. Start it with: ollama serve"
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise

    def generate(self, prompt: str, **kwargs) -> str:
        """Simple generate interface."""
        return self.ask(user=prompt, **kwargs)

