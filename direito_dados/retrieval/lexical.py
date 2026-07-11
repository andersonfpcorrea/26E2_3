"""Pure-Python BM25 lexical retriever and a dense/lexical hybrid fusion.

BM25 (k1=1.5, b=0.75) runs over lowercased whitespace tokens with no external
dependency. `hybrid_search` min-max normalizes each retriever's scores over
its own candidate pool, then fuses them by chunk id as
`alpha * dense + (1 - alpha) * lexical`.
"""

import math

from direito_dados.retrieval.index import Result

_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25Index:
    """Self-contained BM25 ranking over a fixed set of chunks."""

    def __init__(self, chunks, term_freqs, doc_freqs, doc_lens, avgdl):
        self._chunks = {c.id: c for c in chunks}
        self._order = [c.id for c in chunks]
        self._term_freqs = term_freqs
        self._doc_freqs = doc_freqs
        self._doc_lens = doc_lens
        self._avgdl = avgdl
        self._n = len(chunks)

    @classmethod
    def build(cls, chunks) -> "BM25Index":
        term_freqs: dict[str, dict[str, int]] = {}
        doc_freqs: dict[str, int] = {}
        doc_lens: dict[str, int] = {}
        for c in chunks:
            tokens = _tokenize(c.text)
            doc_lens[c.id] = len(tokens)
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            term_freqs[c.id] = tf
            for t in tf:
                doc_freqs[t] = doc_freqs.get(t, 0) + 1
        avgdl = (sum(doc_lens.values()) / len(chunks)) if chunks else 0.0
        return cls(chunks, term_freqs, doc_freqs, doc_lens, avgdl)

    def _score(self, doc_id: str, query_terms: list[str]) -> float:
        tf = self._term_freqs[doc_id]
        dl = self._doc_lens[doc_id]
        score = 0.0
        for t in query_terms:
            f = tf.get(t, 0)
            if f == 0:
                continue
            df = self._doc_freqs.get(t, 0)
            idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1)
            denom = f + _K1 * (1 - _B + _B * (dl / self._avgdl if self._avgdl else 1.0))
            score += idf * (f * (_K1 + 1)) / denom
        return score

    def query(self, text: str, k: int = 5, exclude_revoked: bool = True,
              domain: str | None = None) -> list[Result]:
        query_terms = _tokenize(text)
        results: list[Result] = []
        for cid in self._order:
            chunk = self._chunks[cid]
            meta = chunk.metadata
            if exclude_revoked and meta.get("status") == "revogado":
                continue
            if domain is not None and meta.get("domain") != domain:
                continue
            score = self._score(cid, query_terms)
            if score <= 0:
                continue
            results.append(Result(
                id=cid, text=chunk.text, citation=meta.get("citation", cid),
                score=score, metadata=meta,
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]


def _minmax_normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def hybrid_search(query: str, dense, lexical: BM25Index, embedder, k: int = 5,
                   alpha: float = 0.5, **filters) -> list[Result]:
    candidate_k = max(k * 4, 20)
    dense_results = dense.query(query, embedder, k=candidate_k, **filters)
    lex_results = lexical.query(query, k=candidate_k, **filters)

    dense_norm = _minmax_normalize({r.id: r.score for r in dense_results})
    lex_norm = _minmax_normalize({r.id: r.score for r in lex_results})

    by_id: dict[str, Result] = {}
    for r in dense_results:
        by_id[r.id] = r
    for r in lex_results:
        by_id.setdefault(r.id, r)

    fused: list[Result] = []
    for cid, base in by_id.items():
        d = dense_norm.get(cid, 0.0)
        lex = lex_norm.get(cid, 0.0)
        score = alpha * d + (1 - alpha) * lex
        fused.append(Result(
            id=base.id, text=base.text, citation=base.citation,
            score=score, metadata=base.metadata,
        ))
    fused.sort(key=lambda r: r.score, reverse=True)
    return fused[:k]
