from direito_dados.corpus.models import Article, HierarchyLevel, Norm, VigenciaStatus
from direito_dados.corpus.loader import Corpus
from direito_dados.graph.models import Edge, EdgeKind, NormGraph, Provenance
from direito_dados.analytics.summary import (
    vigencia_summary, hierarchy_distribution, most_amended_articles,
)

def _corpus():
    def art(n, status):
        return Article(norm_id="CP", number=n, caput="c", text="t", status=status)
    cp = Norm(id="CP", title="Código Penal", level=HierarchyLevel.DECRETO_LEI, articles=[
        art("1", VigenciaStatus.VIGENTE), art("2", VigenciaStatus.ALTERADO),
        art("3", VigenciaStatus.REVOGADO)])
    cf = Norm(id="CF", title="Constituição", level=HierarchyLevel.CONSTITUICAO, articles=[
        art("5", VigenciaStatus.VIGENTE)])
    return Corpus(norms=[cp, cf])

def test_vigencia_summary_counts_per_norm():
    s = vigencia_summary(_corpus())
    assert s["CP"] == {"vigente": 1, "alterado": 1, "revogado": 1}
    assert s["CF"] == {"vigente": 1, "alterado": 0, "revogado": 0}

def test_hierarchy_distribution():
    # NOTE: HierarchyLevel.DECRETO_LEI is a value-alias of LEI_ORDINARIA (both
    # rank 3, matching Brazilian norm hierarchy where decreto-lei and lei
    # ordinária share the same standing) — Python's Enum collapses aliases to
    # the canonical member, so `.name` reports "LEI_ORDINARIA" here.
    d = hierarchy_distribution(_corpus())
    assert d["LEI_ORDINARIA"] == 1 and d["CONSTITUICAO"] == 1

def test_most_amended_articles_ranks_by_edge_count():
    g = NormGraph()
    p = Provenance(source="s", extracted_by="x")
    for dst in ["CP:art155", "CP:art155", "CP:art121"]:
        g.add_edge(Edge(kind=EdgeKind.AMENDS, src="ext:L", dst=dst, provenance=p))
    ranked = most_amended_articles(g, top=5)
    assert ranked[0] == ("CP:art155", 2)
    assert ("CP:art121", 1) in ranked
