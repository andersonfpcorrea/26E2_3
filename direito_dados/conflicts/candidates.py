"""Generate candidate conflicting provision pairs via retrieval similarity.

Comparing every pair is O(n^2); topical similarity narrows it to pairs that
plausibly address the same matter (and could therefore conflict).
"""

from dataclasses import dataclass

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import Embedder
from direito_dados.retrieval.index import VectorIndex


@dataclass(frozen=True)
class CandidatePair:
    a: str
    b: str
    similarity: float


def generate_candidates(chunks: list[Chunk], index: VectorIndex, embedder: Embedder,
                        k: int = 5, threshold: float = 0.6) -> list[CandidatePair]:
    best: dict[tuple[str, str], float] = {}
    for chunk in chunks:
        if chunk.metadata.get("status") == "revogado":
            continue
        results = index.query(chunk.text, embedder, k=k + 1, exclude_revoked=True)
        for r in results:
            if r.id == chunk.id:
                continue
            a, b = sorted((chunk.id, r.id))
            key = (a, b)
            if r.score > best.get(key, float("-inf")):
                best[key] = r.score
    pairs = [CandidatePair(a=a, b=b, similarity=s)
             for (a, b), s in best.items() if s >= threshold]
    return sorted(pairs, key=lambda cp: cp.similarity, reverse=True)
