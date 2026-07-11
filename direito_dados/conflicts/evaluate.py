"""Precision / recall / F1 of detected antinomies against a gold set (unordered pairs)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldAntinomy:
    a: str
    b: str


def _key(item) -> frozenset:
    return frozenset({item.a, item.b})


def evaluate_antinomias(detected: list, gold: list) -> dict:
    det = {_key(d) for d in detected}
    gld = {_key(g) for g in gold}
    tp = len(det & gld)
    fp = len(det - gld)
    fn = len(gld - det)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}
