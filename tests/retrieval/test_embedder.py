from direito_dados.retrieval.embedder import Embedder, FakeEmbedder

def test_fake_embedder_is_deterministic_and_shaped():
    e = FakeEmbedder(dim=16)
    a = e.embed_query("matar alguém")
    b = e.embed_query("matar alguém")
    c = e.embed_query("subtrair coisa")
    assert len(a) == 16 and a == b and a != c

def test_fake_embed_passages_batch():
    e = FakeEmbedder(dim=8)
    vecs = e.embed_passages(["um", "dois", "três"])
    assert len(vecs) == 3 and all(len(v) == 8 for v in vecs)

def test_fake_embedder_satisfies_protocol():
    assert isinstance(FakeEmbedder(), Embedder)
