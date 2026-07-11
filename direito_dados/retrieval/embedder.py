"""Embedding interface with a deterministic fake (tests) and an e5 impl (prod)."""

import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FakeEmbedder:
    """Deterministic hash-based embeddings — no network, no model. For tests/CI."""

    def __init__(self, dim: int = 16):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        out: list[float] = []
        i = 0
        while len(out) < self.dim:
            h = hashlib.sha256(f"{i}:{text}".encode("utf-8")).digest()
            for b in h:
                out.append((b / 255.0) * 2.0 - 1.0)
                if len(out) >= self.dim:
                    break
            i += 1
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        return [x / norm for x in out]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class E5Embedder:
    """multilingual-e5-base via sentence-transformers (lazy import)."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        prefixed = [f"passage: {t}" for t in texts]
        return model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        return model.encode([f"query: {text}"], normalize_embeddings=True)[0].tolist()
