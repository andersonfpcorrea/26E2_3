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


def test_caput_skips_lone_line_ordinal_marker():
    text = "Art. 1\nº - Não há crime sem lei anterior que o defina.\n\nArt. 2. Ninguém..."
    arts = split_articles("CP", text)
    art1 = next(a for a in arts if a.number == "1")
    assert not art1.caput.startswith("º")
    assert art1.caput.startswith("Não há crime")


PARAGRAPH_REVOGADO_SAMPLE = """PARTE ESPECIAL
TÍTULO I

Art. 121. Matar alguém:
Pena - reclusão, de seis a vinte anos.
§ 7º ... (Revogado pela Lei nº 13.104, de 2015)

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""


def test_paragraph_level_revogado_does_not_revoke_whole_article():
    arts = split_articles("CP", PARAGRAPH_REVOGADO_SAMPLE)
    art121 = next(a for a in arts if a.number == "121")
    art240 = next(a for a in arts if a.number == "240")

    assert art121.status == VigenciaStatus.ALTERADO
    assert art240.status == VigenciaStatus.REVOGADO

    in_force = [a for a in arts if a.status != VigenciaStatus.REVOGADO]
    assert art121 in in_force
    assert art240 not in in_force


def test_chained_article_suffixes_are_distinct():
    text = "Art. 359-M. Primeiro.\n\nArt. 359-M-A. Segundo.\n\nArt. 359-M-B. Terceiro."
    nums = [a.number for a in split_articles("CP", text)]
    assert nums == ["359-M", "359-M-A", "359-M-B"]


def test_html_to_plain_text_keeps_articles_and_annotations():
    from direito_dados.corpus.fetch import html_to_plain_text

    html = (
        "<html><head><style>x{}</style></head><body>"
        "<p>Art. 155. Subtrair coisa alheia "
        "(Redação dada pela Lei nº 13.654, de 2018).</p>"
        "<script>ignore()</script></body></html>"
    )
    text = html_to_plain_text(html)
    assert "Art. 155." in text
    assert "Lei nº 13.654" in text
    assert "ignore()" not in text


RUBRICA_SAMPLE = """CAPÍTULO I
DOS CRIMES CONTRA A VIDA
Homicídio simples
Art. 121. Matar alguém:
Pena - reclusão, de seis a vinte anos.

Furto
Art. 155 - Subtrair, para si ou para outrem, coisa alheia móvel:
Pena - reclusão, de um a quatro anos (Redação dada pela Lei nº 13.654, de 2018).

Art. 214 -
(Revogado pela Lei nº
12.015, de 2009)
Violação sexual mediante fraude
(Redação
dada pela Lei nº 12.015, de 2009)
Art. 215.  Ter conjunção carnal ou praticar outro ato libidinoso, mediante fraude:
Pena - reclusão, de 2 (dois) a 6 (seis) anos.
"""


def test_rubrica_attaches_to_following_article():
    arts = {a.number: a for a in split_articles("CP", RUBRICA_SAMPLE)}
    assert arts["121"].rubrica == "Homicídio simples"
    assert arts["155"].rubrica == "Furto"
    assert arts["215"].rubrica == "Violação sexual mediante fraude"


def test_rubrica_removed_from_previous_article_text():
    arts = {a.number: a for a in split_articles("CP", RUBRICA_SAMPLE)}
    assert "Furto" not in arts["121"].text
    assert "Violação sexual" not in arts["214"].text


def test_structural_headings_are_not_rubricas():
    arts = {a.number: a for a in split_articles("CP", RUBRICA_SAMPLE)}
    assert "CAPÍTULO" not in arts["121"].rubrica
    assert "DOS CRIMES" not in arts["121"].rubrica


def test_pena_line_is_never_stolen_as_rubrica():
    text = "Art. 1. Conduta:\nPena - detenção\n\nArt. 2. Outra conduta."
    arts = {a.number: a for a in split_articles("CP", text)}
    assert arts["2"].rubrica == ""
    assert "Pena - detenção" in arts["1"].text


def test_annotation_only_tail_is_not_a_rubrica():
    text = ("Art. 1. Conduta punida.\n(Incluído pela Lei nº 9.999, de 1999)\n\n"
            "Art. 2. Outra conduta.")
    arts = {a.number: a for a in split_articles("CP", text)}
    assert arts["2"].rubrica == ""


def test_revoked_caput_detection_unaffected_by_rubrica_move():
    arts = {a.number: a for a in split_articles("CP", RUBRICA_SAMPLE)}
    assert arts["214"].status == VigenciaStatus.REVOGADO
    # The rubrica's own trailing annotation stays where it was (annotations
    # never move between blocks), so in this minimal fixture art. 215 has no
    # annotation of its own and remains VIGENTE. (In the real corpus art. 215
    # carries inline annotations and is ALTERADO.)
    assert arts["215"].status == VigenciaStatus.VIGENTE
