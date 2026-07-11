"""Build a NormGraph from a parsed Corpus.

Populates NORM and PROVISION nodes and the AMENDS/REVOKES edges stated directly
in Planalto annotations (authoritative facts -> VERIFIED). REFERENCES,
CONFLICT_CANDIDATE and ENACTED_BY are part of the schema but are populated by
later modules (citation parsing, the conflicts detector, the attribution engine).
"""

from direito_dados.corpus.loader import Corpus
from direito_dados.corpus.models import Article, Norm
from direito_dados.graph.models import (
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    NormGraph,
    Provenance,
    VerificationState,
)

_KIND_TO_EDGE = {
    "redacao": EdgeKind.AMENDS,
    "incluido": EdgeKind.AMENDS,
    "renumerado": EdgeKind.AMENDS,
    "revogado": EdgeKind.REVOKES,
}


def provision_id(norm_id: str, number: str) -> str:
    return f"{norm_id}:art{number}"


def _amending_norm_id(law_ref: str, year: int | None) -> str:
    ref = law_ref.replace(" ", "_")
    return f"ext:{ref}" + (f";{year}" if year else "")


def build_graph(corpus: Corpus) -> NormGraph:
    graph = NormGraph()
    for norm in corpus.norms:
        graph.add_node(Node(
            id=norm.id, kind=NodeKind.NORM, label=norm.title,
            domain=norm.domain, attrs={"urn": norm.urn},
        ))
        for art in norm.articles:
            graph.add_node(Node(
                id=provision_id(norm.id, art.number),
                kind=NodeKind.PROVISION, label=art.citation, domain=norm.domain,
                attrs={"status": art.status.value, "urn": norm.urn},
            ))
            _add_annotation_edges(graph, norm, art)
    return graph


def _add_annotation_edges(graph: NormGraph, norm: Norm, art: Article) -> None:
    dst = provision_id(norm.id, art.number)
    for ann in art.annotations:
        edge_kind = _KIND_TO_EDGE.get(ann.kind)
        if edge_kind is None:
            continue  # 'vide' is a cross-reference note, not an amend/revoke
        src = _amending_norm_id(ann.law_ref, ann.year)
        if graph.node(src) is None:
            graph.add_node(Node(
                id=src, kind=NodeKind.NORM, label=ann.law_ref,
                attrs={"external": True, "year": ann.year},
            ))
        graph.add_edge(Edge(
            kind=edge_kind, src=src, dst=dst,
            provenance=Provenance(source=f"planalto:{norm.id}",
                                  extracted_by="annotation-parser"),
            verification_state=VerificationState.VERIFIED,
            confidence=1.0,
            attrs={"law_ref": ann.law_ref, "year": ann.year},
        ))
