"""Tests for graph enrichment (ENACTED_BY edges) — pure, on hand-built graphs."""

import json
from pathlib import Path

from direito_dados.attribution.enrich import add_enacted_by_edges, load_authorship
from direito_dados.attribution.models import Author, Authorship
from direito_dados.graph.models import EdgeKind, Node, NodeKind, NormGraph, VerificationState


def _graph_with_external_norm() -> NormGraph:
    graph = NormGraph()
    graph.add_node(Node(id="CP", kind=NodeKind.NORM, label="Código Penal", domain="penal"))
    graph.add_node(Node(
        id="ext:Lei_nº_13.964;2019", kind=NodeKind.NORM, label="Lei nº 13.964",
        attrs={"external": True, "year": 2019},
    ))
    return graph


def test_add_enacted_by_edges_creates_author_node_and_verified_edge():
    graph = _graph_with_external_norm()
    records = [
        Authorship(
            law_ref="Lei nº 13.964", numero=13964, ano=2019, tipo="LEI",
            status="resolved", origin_bill="PL 10372/2018", origin_house="CD",
            authors=[Author(name="José Rocha", kind="DEPUTADO", party="PL", uf="BA")],
            source="senado:processo/7850496",
        )
    ]

    added = add_enacted_by_edges(graph, records)

    assert added == 1
    author_node = graph.node("author:José Rocha")
    assert author_node is not None
    assert author_node.kind == NodeKind.AUTHOR
    assert author_node.attrs["party"] == "PL"
    assert author_node.attrs["uf"] == "BA"

    edges = graph.edges_of_kind(EdgeKind.ENACTED_BY)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.src == "ext:Lei_nº_13.964;2019"
    assert edge.dst == "author:José Rocha"
    assert edge.verification_state == VerificationState.VERIFIED
    assert edge.confidence == 1.0
    assert edge.provenance.source == "senado:processo/7850496"
    assert edge.attrs["origin_bill"] == "PL 10372/2018"
    assert "partido = filiação atual" in edge.attrs["party_note"]


def test_add_enacted_by_edges_dedups_author_node_across_laws():
    graph = _graph_with_external_norm()
    graph.add_node(Node(
        id="ext:Lei_nº_1;2020", kind=NodeKind.NORM, label="Lei nº 1",
        attrs={"external": True, "year": 2020},
    ))
    author = Author(name="José Rocha", kind="DEPUTADO", party="PL")
    records = [
        Authorship(law_ref="Lei nº 13.964", numero=13964, ano=2019, tipo="LEI",
                   status="resolved", authors=[author], source="s:1"),
        Authorship(law_ref="Lei nº 1", numero=1, ano=2020, tipo="LEI",
                   status="resolved", authors=[author], source="s:2"),
    ]
    add_enacted_by_edges(graph, records)
    assert len(graph.nodes_of_kind(NodeKind.AUTHOR)) == 1
    assert len(graph.edges_of_kind(EdgeKind.ENACTED_BY)) == 2


def test_add_enacted_by_edges_skips_unresolved_and_unmatched():
    graph = _graph_with_external_norm()
    records = [
        Authorship(law_ref="Lei nº 13.964", numero=13964, ano=2019, tipo="LEI",
                   status="not_found"),
        Authorship(law_ref="Lei nº 99999", numero=99999, ano=2099, tipo="LEI",
                   status="resolved", authors=[Author(name="Ninguém", kind="DEPUTADO")]),
    ]
    added = add_enacted_by_edges(graph, records)
    assert added == 0
    assert graph.edges_of_kind(EdgeKind.ENACTED_BY) == []


def test_load_authorship_round_trips_from_file(tmp_path):
    from direito_dados.attribution.models import to_json

    path = tmp_path / "authorship.json"
    record = Authorship(law_ref="Lei nº 1", numero=1, ano=2020, tipo="LEI", status="resolved")
    path.write_text(json.dumps(to_json([record], fetched_at="t", source="s")), encoding="utf-8")

    loaded = load_authorship(path)
    assert loaded == [record]
