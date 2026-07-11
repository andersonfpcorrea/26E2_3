"""Amendment-timeline analytics over the norm-graph.

The graph's AMENDS/REVOKES edges already carry the amending law and year parsed
from Planalto annotations, so the mutation timeline of the microsystem is free.
"""

from direito_dados.graph.models import EdgeKind, NormGraph

_TIMELINE_KINDS = {EdgeKind.AMENDS, EdgeKind.REVOKES}


def amendment_events(graph: NormGraph) -> list[dict]:
    events: list[dict] = []
    for e in graph.edges:
        if e.kind not in _TIMELINE_KINDS:
            continue
        events.append({
            "year": e.attrs.get("year"),
            "kind": e.kind.value,
            "law_ref": e.attrs.get("law_ref", ""),
            "target": e.dst,
            "norm_id": e.dst.split(":")[0],
        })
    return events


def amendments_by_year(graph: NormGraph) -> dict[int, int]:
    counts: dict[int, int] = {}
    for ev in amendment_events(graph):
        y = ev["year"]
        if y is None:
            continue
        counts[y] = counts.get(y, 0) + 1
    return counts


def amendments_by_decade(graph: NormGraph) -> dict[int, int]:
    counts: dict[int, int] = {}
    for y, n in amendments_by_year(graph).items():
        decade = (y // 10) * 10
        counts[decade] = counts.get(decade, 0) + n
    return counts


def amendments_per_norm(graph: NormGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in amendment_events(graph):
        nid = ev["norm_id"]
        counts[nid] = counts.get(nid, 0) + 1
    return counts
