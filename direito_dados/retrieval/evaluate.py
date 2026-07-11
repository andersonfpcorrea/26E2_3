"""Retrieval evaluation: hit-rate@k and MRR against a small gold set."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldItem:
    question: str
    relevant_ids: list[str]


def evaluate(retriever_fn, gold: list[GoldItem], k: int = 5) -> dict:
    hits = 0
    rr_sum = 0.0
    for item in gold:
        results = retriever_fn(item.question, k)[:k]
        relevant = set(item.relevant_ids)
        rank = next((i + 1 for i, r in enumerate(results) if r.id in relevant), None)
        if rank is not None:
            hits += 1
            rr_sum += 1.0 / rank
    n = len(gold)
    return {"hit_rate": hits / n if n else 0.0, "mrr": rr_sum / n if n else 0.0, "n": n}
