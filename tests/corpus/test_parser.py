from direito_dados.corpus.models import HierarchyLevel, VigenciaStatus
from direito_dados.corpus.parser import parse_norm, split_articles

SAMPLE = """PARTE ESPECIAL
TÍTULO I

Art. 121. Matar alguém:
Pena - reclusão, de seis a vinte anos.

Art. 155. Subtrair, para si ou para outrem, coisa alheia móvel:
Pena - reclusão, de um a quatro anos (Redação dada pela Lei nº 13.654, de 2018).

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""


def test_splits_on_article_headers():
    arts = split_articles("CP", SAMPLE)
    assert [a.number for a in arts] == ["121", "155", "240"]


def test_caput_is_first_line_of_article():
    arts = split_articles("CP", SAMPLE)
    assert arts[0].caput.startswith("Matar alguém")


def test_amended_article_marked_alterado():
    arts = split_articles("CP", SAMPLE)
    art155 = next(a for a in arts if a.number == "155")
    assert art155.status == VigenciaStatus.ALTERADO
    assert any(ann.year == 2018 for ann in art155.annotations)


def test_revoked_article_marked_revogado():
    arts = split_articles("CP", SAMPLE)
    art240 = next(a for a in arts if a.number == "240")
    assert art240.status == VigenciaStatus.REVOGADO


def test_text_before_first_article_ignored():
    arts = split_articles("CP", SAMPLE)
    assert all("PARTE ESPECIAL" not in a.text for a in arts)


def test_parse_norm_builds_norm_object():
    norm = parse_norm("CP", "Código Penal", HierarchyLevel.DECRETO_LEI, SAMPLE)
    assert norm.id == "CP"
    assert norm.level == HierarchyLevel.DECRETO_LEI
    assert norm.article("121") is not None
