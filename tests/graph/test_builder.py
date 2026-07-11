from direito_dados.corpus.loader import load_corpus
from direito_dados.corpus.registry import NormSpec
from direito_dados.graph import EdgeKind, NodeKind, VerificationState, build_graph, provision_id

FIXTURE = """Art. 121. Matar alguém:
Pena - reclusão.

Art. 155. Subtrair coisa alheia móvel:
Pena - reclusão (Redação dada pela Lei nº 13.654, de 2018).

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""


def _corpus(tmp_path):
    (tmp_path / "CP.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="CP", title="Código Penal", norm_type="decreto_lei",
                    source_url="http://x", filename="CP.txt",
                    urn="urn:lex:br:federal:decreto.lei:1940-12-07;2848", domain="penal")
    return load_corpus(str(tmp_path), specs=[spec])


def test_builds_norm_and_provision_nodes(tmp_path):
    g = build_graph(_corpus(tmp_path))
    assert g.node("CP").kind == NodeKind.NORM
    assert g.node("CP").domain == "penal"
    assert g.node(provision_id("CP", "155")).kind == NodeKind.PROVISION
    assert g.node(provision_id("CP", "155")).attrs["urn"].endswith(";2848")


def test_amends_edge_from_redacao_annotation(tmp_path):
    g = build_graph(_corpus(tmp_path))
    amends = g.edges_of_kind(EdgeKind.AMENDS)
    assert any(e.dst == provision_id("CP", "155") for e in amends)
    edge = next(e for e in amends if e.dst == provision_id("CP", "155"))
    assert edge.verification_state == VerificationState.VERIFIED
    assert edge.attrs["law_ref"] == "Lei nº 13.654"
    assert edge.attrs["year"] == 2018


def test_revokes_edge_from_revogado_annotation(tmp_path):
    g = build_graph(_corpus(tmp_path))
    revokes = g.edges_of_kind(EdgeKind.REVOKES)
    assert [e.dst for e in revokes] == [provision_id("CP", "240")]


def test_amending_law_becomes_external_norm_node(tmp_path):
    g = build_graph(_corpus(tmp_path))
    amends = g.edges_of_kind(EdgeKind.AMENDS)
    src_id = next(e.src for e in amends if e.dst == provision_id("CP", "155"))
    assert g.node(src_id).attrs.get("external") is True


def test_unamended_article_has_no_edges(tmp_path):
    g = build_graph(_corpus(tmp_path))
    assert g.edges_to(provision_id("CP", "121")) == []
