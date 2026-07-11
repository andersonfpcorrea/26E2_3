import pytest
pytest.importorskip("chromadb")

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import FakeEmbedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.retrieval.lexical import BM25Index, hybrid_search

def _chunks():
    def c(id_, text, status="vigente"):
        return Chunk(id=id_, text=text, metadata={
            "norm_id": "CP", "article": id_.split("art")[1], "urn": "urn:x",
            "domain": "penal", "hierarchy_level": 3, "status": status, "citation": id_})
    return [c("CP:art121","matar alguém homicídio"), c("CP:art155","subtrair coisa furto"),
            c("CP:art240","adultério revogado", status="revogado")]

def test_bm25_finds_exact_term_and_excludes_revoked():
    idx = BM25Index.build(_chunks())
    res = idx.query("homicídio", k=5)
    assert res[0].id == "CP:art121"
    assert "CP:art240" not in {r.id for r in idx.query("adultério", k=5)}

def test_hybrid_returns_topk_by_fused_score():
    e = FakeEmbedder()
    dense = VectorIndex.build(_chunks(), e)
    lex = BM25Index.build(_chunks())
    res = hybrid_search("homicídio matar", dense, lex, e, k=2)
    assert len(res) <= 2
    assert res == sorted(res, key=lambda r: r.score, reverse=True)
    assert "CP:art240" not in {r.id for r in res}
