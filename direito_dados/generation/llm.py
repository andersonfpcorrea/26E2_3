"""LLM client interface: a deterministic FakeLLM (tests) and an Ollama impl (prod)."""

from typing import Protocol, runtime_checkable

import requests


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None, format=None) -> str: ...


class FakeLLM:
    """Deterministic LLM stand-in for tests. `response` is a str or (prompt, system)->str."""

    def __init__(self, response):
        self._response = response
        self.last_prompt: str | None = None
        self.last_system: str | None = None

    def generate(self, prompt: str, system: str | None = None, format=None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        if callable(self._response):
            return self._response(prompt, system)
        return self._response


class OllamaClient:
    """Local Ollama generation via the HTTP API (no data leaves the machine)."""

    def __init__(self, model: str = "llama3.1", host: str = "http://localhost:11434",
                 timeout: int = 120, json_format: bool = True):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        # Every call in this project expects structured JSON; Ollama's
        # `format: "json"` constrains the model to emit valid JSON.
        self.json_format = json_format

    def generate(self, prompt: str, system: str | None = None, format=None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        # A caller-supplied JSON schema constrains output to that schema; else
        # fall back to plain "json" mode (valid JSON, unconstrained shape).
        if format is not None:
            payload["format"] = format
        elif self.json_format:
            payload["format"] = "json"
        resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["response"]


def ollama_available(host: str = "http://localhost:11434") -> bool:
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def ollama_has_model(model: str, host: str = "http://localhost:11434") -> bool:
    """True iff the Ollama service is up and `model` (matched by name prefix) is pulled."""
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(n == model or n.startswith(f"{model}:") for n in names)
    except requests.RequestException:
        return False
