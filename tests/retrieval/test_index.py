import pytest

pytest.importorskip("chromadb")

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import FakeEmbedder
from direito_dados.retrieval.index import Result, VectorIndex

def _chunks():
    def c(id_, text, status="vigente", domain="penal"):
        return Chunk(id=id_, text=text, metadata={
            "norm_id": id_.split(":")[0], "article": id_.split("art")[1], "urn": "urn:x",
            "domain": domain, "hierarchy_level": 3, "status": status, "citation": id_})
    return [
        c("CP:art121", "Matar alguém homicídio pena reclusão"),
        c("CP:art155", "Subtrair coisa alheia móvel furto"),
        c("CP:art240", "Adultério dispositivo antigo", status="revogado"),
        c("CDC:art6", "Direitos básicos do consumidor", domain="consumidor"),
    ]

def test_query_returns_ranked_results(tmp_path):
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    res = idx.query("homicídio matar", e, k=3)
    assert res and isinstance(res[0], Result)
    assert res == sorted(res, key=lambda r: r.score, reverse=True)

def test_query_excludes_revoked_by_default(tmp_path):
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    ids = {r.id for r in idx.query("adultério", e, k=10)}
    assert "CP:art240" not in ids

def test_query_can_include_revoked_when_asked(tmp_path):
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    ids = {r.id for r in idx.query("adultério", e, k=10, exclude_revoked=False)}
    assert "CP:art240" in ids

def test_query_domain_filter(tmp_path):
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    ids = {r.id for r in idx.query("consumidor", e, k=10, domain="consumidor")}
    assert ids == {"CDC:art6"}
