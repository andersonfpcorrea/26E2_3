import pytest
pytest.importorskip("chromadb")

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import FakeEmbedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.conflicts.candidates import CandidatePair, generate_candidates

def _chunks():
    def c(id_, text, status="vigente"):
        return Chunk(id=id_, text=text, embed_text=text, metadata={
            "norm_id": id_.split(":")[0], "article": id_.split("art")[1], "urn": "u",
            "domain": "penal", "hierarchy_level": 3, "status": status, "citation": id_})
    return [c("CP:art121","matar alguém homicídio"), c("CP:art121-A","matar alguém contexto"),
            c("L8072:art1","crimes hediondos homicídio qualificado"),
            c("CP:art240","adultério", status="revogado")]

def test_candidates_are_canonical_and_deduped():
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    cands = generate_candidates(_chunks(), idx, e, k=5, threshold=-1.0)
    for cp in cands:
        assert isinstance(cp, CandidatePair) and cp.a <= cp.b
    pairs = {(cp.a, cp.b) for cp in cands}
    assert len(pairs) == len(cands)   # no duplicates

def test_candidates_exclude_revoked_and_self():
    e = FakeEmbedder()
    idx = VectorIndex.build(_chunks(), e)
    cands = generate_candidates(_chunks(), idx, e, k=5, threshold=-1.0)
    ids_in_pairs = {x for cp in cands for x in (cp.a, cp.b)}
    assert "CP:art240" not in ids_in_pairs         # revoked excluded
    assert all(cp.a != cp.b for cp in cands)        # no self-pairs
