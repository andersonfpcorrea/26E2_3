import json
from direito_dados.graph.models import (
    Edge, EdgeKind, Node, NodeKind, NormGraph, Provenance,
)
from direito_dados.analytics.network import to_network_data

def _graph():
    g = NormGraph()
    g.add_node(Node(id="CP", kind=NodeKind.NORM, label="Código Penal", domain="penal"))
    g.add_node(Node(id="CP:art155", kind=NodeKind.PROVISION, label="CP art. 155",
                    domain="penal", attrs={"status": "alterado"}))
    g.add_node(Node(id="ext:Lei_1", kind=NodeKind.NORM, label="Lei nº 1",
                    attrs={"external": True}))
    g.add_edge(Edge(kind=EdgeKind.AMENDS, src="ext:Lei_1", dst="CP:art155",
                    provenance=Provenance(source="s", extracted_by="x"),
                    attrs={"year": 2018}))
    return g

def test_export_is_json_serializable_with_expected_shape():
    data = to_network_data(_graph())
    assert set(data) == {"nodes", "edges"}
    json.dumps(data)  # must not raise
    prov = next(n for n in data["nodes"] if n["id"] == "CP:art155")
    assert prov["status"] == "alterado" and prov["kind"] == "provision"

def test_external_nodes_excluded_by_default():
    data = to_network_data(_graph())
    ids = {n["id"] for n in data["nodes"]}
    assert "ext:Lei_1" not in ids
    assert data["edges"] == []   # the only edge touched an external node

def test_external_included_when_requested():
    data = to_network_data(_graph(), include_external=True)
    ids = {n["id"] for n in data["nodes"]}
    assert "ext:Lei_1" in ids
    assert data["edges"][0]["year"] == 2018
