from direito_dados.graph.models import (
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    NormGraph,
    Provenance,
    VerificationState,
)


def _prov():
    return Provenance(source="planalto:CP", extracted_by="annotation-parser")


def test_add_and_lookup_node():
    g = NormGraph()
    g.add_node(Node(id="CP", kind=NodeKind.NORM, label="Código Penal", domain="penal"))
    assert g.node("CP").label == "Código Penal"
    assert g.node("missing") is None


def test_edges_default_to_candidate_full_confidence():
    e = Edge(kind=EdgeKind.CONFLICT_CANDIDATE, src="a", dst="b", provenance=_prov())
    assert e.verification_state == VerificationState.CANDIDATE
    assert e.confidence == 1.0


def test_query_edges_by_kind_and_endpoint():
    g = NormGraph()
    g.add_edge(Edge(kind=EdgeKind.REVOKES, src="ext:Lei_99", dst="CP:art240",
                    provenance=_prov(), verification_state=VerificationState.VERIFIED))
    g.add_edge(Edge(kind=EdgeKind.AMENDS, src="ext:Lei_13", dst="CP:art155",
                    provenance=_prov(), verification_state=VerificationState.VERIFIED))
    assert len(g.edges_of_kind(EdgeKind.REVOKES)) == 1
    assert g.edges_to("CP:art240")[0].kind == EdgeKind.REVOKES
    assert g.edges_from("ext:Lei_13")[0].dst == "CP:art155"


def test_nodes_of_kind_filters():
    g = NormGraph()
    g.add_node(Node(id="CP", kind=NodeKind.NORM, label="Código Penal"))
    g.add_node(Node(id="CP:art155", kind=NodeKind.PROVISION, label="CP art. 155"))
    assert [n.id for n in g.nodes_of_kind(NodeKind.PROVISION)] == ["CP:art155"]


def test_domain_field_accepts_any_string():
    n = Node(id="X", kind=NodeKind.NORM, label="Qualquer", domain="tributario")
    assert n.domain == "tributario"
