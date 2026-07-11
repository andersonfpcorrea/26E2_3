import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from direito_dados.corpus import load_corpus, NORMS
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex


def test_e5_retrieves_homicide_article_for_natural_query(tmp_path):
    corpus = load_corpus("data/raw", specs=[NORMS["CP"]])
    chunks = chunk_corpus(corpus)
    e = E5Embedder()
    idx = VectorIndex.build(chunks, e)
    res = idx.query("qual a pena para quem mata alguém?", e, k=5)
    ids = {r.id for r in res}
    assert "CP:art121" in ids            # homicídio
    assert all(r.metadata["status"] != "revogado" for r in res)
