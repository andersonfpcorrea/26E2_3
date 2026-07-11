from direito_dados.corpus.loader import load_corpus
from direito_dados.corpus.registry import NormSpec
from direito_dados.retrieval.chunks import Chunk, chunk_corpus

FIXTURE = """Art. 121. Matar alguém:
Pena - reclusão.

Art. 155. Subtrair coisa alheia (Redação dada pela Lei nº 13.654, de 2018).

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""

def _corpus(tmp_path):
    (tmp_path / "CP.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="CP", title="Código Penal", norm_type="decreto_lei",
                    source_url="http://x", filename="CP.txt",
                    urn="urn:lex:br:federal:decreto.lei:1940-12-07;2848", domain="penal")
    return load_corpus(str(tmp_path), specs=[spec])

def test_one_chunk_per_article_with_metadata(tmp_path):
    chunks = chunk_corpus(_corpus(tmp_path))
    by_id = {c.id: c for c in chunks}
    assert "CP:art121" in by_id
    m = by_id["CP:art121"].metadata
    assert m["norm_id"] == "CP" and m["article"] == "121" and m["domain"] == "penal"
    assert m["urn"].endswith(";2848") and isinstance(m["hierarchy_level"], int)
    assert m["citation"] == "CP art. 121"

def test_revoked_article_chunk_marked_in_metadata(tmp_path):
    chunks = chunk_corpus(_corpus(tmp_path))
    art240 = next(c for c in chunks if c.id == "CP:art240")
    assert art240.metadata["status"] == "revogado"
