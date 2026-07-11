from direito_dados.corpus.loader import Corpus, load_corpus
from direito_dados.corpus.registry import NormSpec
from direito_dados.corpus.models import VigenciaStatus

FIXTURE = """Art. 1. Norma vigente qualquer.

Art. 2. (Revogado pela Lei nº 99, de 2001)
"""


def test_load_norm_and_corpus_from_raw_dir(tmp_path):
    (tmp_path / "TST.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="TST", title="Teste", norm_type="lei_ordinaria",
                    source_url="http://x", filename="TST.txt")
    corpus = load_corpus(str(tmp_path), specs=[spec])
    assert isinstance(corpus, Corpus)
    assert corpus.norm("TST") is not None
    assert len(corpus.all_articles()) == 2


def test_in_force_articles_excludes_revogado(tmp_path):
    (tmp_path / "TST.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="TST", title="Teste", norm_type="lei_ordinaria",
                    source_url="http://x", filename="TST.txt")
    corpus = load_corpus(str(tmp_path), specs=[spec])
    in_force = corpus.in_force_articles()
    assert [a.number for a in in_force] == ["1"]
    assert all(a.status != VigenciaStatus.REVOGADO for a in in_force)
