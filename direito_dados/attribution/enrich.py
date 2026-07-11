"""Enrich a NormGraph with ENACTED_BY edges from resolved authorship records.

Reuses `_amending_norm_id` from `direito_dados.graph.builder` — the same
convention that already assigns ids to the external norm nodes created by
AMENDS/REVOKES edges — so a resolved `Authorship` record matches its law
node exactly.
"""

import json
from pathlib import Path

from direito_dados.attribution.models import Authorship, from_json
from direito_dados.graph.builder import _amending_norm_id
from direito_dados.graph.models import (
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    NormGraph,
    Provenance,
    VerificationState,
)

_PARTY_NOTE = "partido = filiação atual/última registrada"


def load_authorship(path: str | Path) -> list[Authorship]:
    """Load the committed `data/attribution/authorship.json` dataset."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return from_json(data)


def _author_node_id(name: str) -> str:
    return f"author:{name}"


def add_enacted_by_edges(graph: NormGraph, records: list[Authorship]) -> int:
    """Add one AUTHOR node (deduped by id) and one VERIFIED ENACTED_BY edge
    per (resolved record, author) pair whose law matches an external norm
    node already on the graph. Returns the number of edges added."""
    added = 0
    for record in records:
        if record.status != "resolved" or not record.authors:
            continue
        law_node_id = _amending_norm_id(record.law_ref, record.ano)
        if graph.node(law_node_id) is None:
            continue

        for author in record.authors:
            author_node_id = _author_node_id(author.name)
            if graph.node(author_node_id) is None:
                graph.add_node(Node(
                    id=author_node_id, kind=NodeKind.AUTHOR, label=author.name,
                    attrs={"party": author.party, "uf": author.uf, "kind": author.kind},
                ))
            graph.add_edge(Edge(
                kind=EdgeKind.ENACTED_BY, src=law_node_id, dst=author_node_id,
                provenance=Provenance(source=record.source, extracted_by="attribution-adapter"),
                verification_state=VerificationState.VERIFIED,
                confidence=1.0,
                attrs={
                    "origin_bill": record.origin_bill,
                    "origin_house": record.origin_house,
                    "party_note": _PARTY_NOTE,
                },
            ))
            added += 1
    return added
