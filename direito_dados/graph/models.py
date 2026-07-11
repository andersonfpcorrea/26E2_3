"""Corpus-agnostic norm-graph: the shared spine read by retrieval, conflicts, analytics.

Nodes are norms and provisions; edges are relationships between them (amends,
revokes, references, conflict_candidate, enacted_by). Every edge records its
provenance, a verification_state (candidate vs verified) and a confidence, so the
same structure serves a small verified microsystem today and a whole-corpus,
candidate-surfacing platform later. Nothing here is domain-specific.
"""

from dataclasses import dataclass, field
from enum import Enum


class NodeKind(Enum):
    NORM = "norm"
    PROVISION = "provision"


class EdgeKind(Enum):
    AMENDS = "amends"
    REVOKES = "revokes"
    REFERENCES = "references"
    CONFLICT_CANDIDATE = "conflict_candidate"
    ENACTED_BY = "enacted_by"


class VerificationState(Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"


@dataclass(frozen=True)
class Provenance:
    source: str
    extracted_by: str


@dataclass
class Node:
    id: str
    kind: NodeKind
    label: str
    domain: str = ""
    attrs: dict = field(default_factory=dict)


@dataclass
class Edge:
    kind: EdgeKind
    src: str
    dst: str
    provenance: Provenance
    verification_state: VerificationState = VerificationState.CANDIDATE
    confidence: float = 1.0
    attrs: dict = field(default_factory=dict)


@dataclass
class NormGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def node(self, id: str) -> Node | None:
        return self.nodes.get(id)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def edges_of_kind(self, kind: EdgeKind) -> list[Edge]:
        return [e for e in self.edges if e.kind == kind]

    def edges_from(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.src == node_id]

    def edges_to(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.dst == node_id]

    def nodes_of_kind(self, kind: NodeKind) -> list[Node]:
        return [n for n in self.nodes.values() if n.kind == kind]
