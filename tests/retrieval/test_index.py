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


class _CountingEmbedder(FakeEmbedder):
    def __init__(self):
        super().__init__()
        self.passage_calls = 0

    def embed_passages(self, texts):
        self.passage_calls += 1
        return super().embed_passages(texts)


def test_open_or_build_reuses_persisted_index(tmp_path):
    e = _CountingEmbedder()
    chunks = _chunks()
    idx1 = VectorIndex.open_or_build(chunks, e, persist_dir=str(tmp_path))
    assert e.passage_calls == 1                       # built once
    idx2 = VectorIndex.open_or_build(chunks, e, persist_dir=str(tmp_path))
    assert e.passage_calls == 1                       # reopened, NOT re-embedded
    ids = {r.id for r in idx2.query("homicídio matar", e, k=3)}
    assert ids  # queries work against the reopened index


def test_open_or_build_rebuilds_when_corpus_changes(tmp_path):
    e = _CountingEmbedder()
    chunks = _chunks()
    VectorIndex.open_or_build(chunks, e, persist_dir=str(tmp_path))
    changed = chunks[:-1]                             # one chunk removed
    VectorIndex.open_or_build(changed, e, persist_dir=str(tmp_path))
    assert e.passage_calls == 2                       # mismatch -> rebuilt
