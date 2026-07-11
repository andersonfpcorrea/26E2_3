"""LLM client interface: a deterministic FakeLLM (tests) and an Ollama impl (prod)."""

from typing import Protocol, runtime_checkable

import requests


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str: ...


class FakeLLM:
    """Deterministic LLM stand-in for tests. `response` is a str or (prompt, system)->str."""

    def __init__(self, response):
        self._response = response
        self.last_prompt: str | None = None
        self.last_system: str | None = None

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        if callable(self._response):
            return self._response(prompt, system)
        return self._response


class OllamaClient:
    """Local Ollama generation via the HTTP API (no data leaves the machine)."""

    def __init__(self, model: str = "llama3.1", host: str = "http://localhost:11434",
                 timeout: int = 120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, system: str | None = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["response"]


def ollama_available(host: str = "http://localhost:11434") -> bool:
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False
