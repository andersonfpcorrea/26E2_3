"""Vigência, hierarchy, and amendment-intensity summaries over corpus + graph."""

from direito_dados.corpus.loader import Corpus
from direito_dados.corpus.models import VigenciaStatus
from direito_dados.graph.models import EdgeKind, NormGraph

_TIMELINE_KINDS = {EdgeKind.AMENDS, EdgeKind.REVOKES}


def vigencia_summary(corpus: Corpus) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for norm in corpus.norms:
        counts = {s.value: 0 for s in VigenciaStatus}
        for art in norm.articles:
            counts[art.status.value] += 1
        out[norm.id] = counts
    return out


def hierarchy_distribution(corpus: Corpus) -> dict[str, int]:
    out: dict[str, int] = {}
    for norm in corpus.norms:
        out[norm.level.name] = out.get(norm.level.name, 0) + 1
    return out


def most_amended_articles(graph: NormGraph, top: int = 10) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for e in graph.edges:
        if e.kind in _TIMELINE_KINDS:
            counts[e.dst] = counts.get(e.dst, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top]
