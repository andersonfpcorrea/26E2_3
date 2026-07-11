from direito_dados.corpus.annotations import extract_annotations, status_from_annotations
from direito_dados.corpus.models import VigenciaStatus


def test_extract_redacao_annotation():
    text = "Pena - reclusão (Redação dada pela Lei nº 13.964, de 2019)"
    anns = extract_annotations(text)
    assert len(anns) == 1
    assert anns[0].kind == "redacao"
    assert anns[0].law_ref == "Lei nº 13.964"
    assert anns[0].year == 2019


def test_extract_revogado_annotation():
    text = "Art. 240. (Revogado pela Lei nº 11.106, de 2005)"
    anns = extract_annotations(text)
    assert anns[0].kind == "revogado"
    assert anns[0].year == 2005


def test_extract_multiple_annotations():
    text = (
        "Caput (Incluído pela Lei nº 12.015, de 2009). "
        "§ 1º (Redação dada pela Lei nº 13.718, de 2018)"
    )
    anns = extract_annotations(text)
    kinds = {a.kind for a in anns}
    assert kinds == {"incluido", "redacao"}


def test_annotation_without_year_is_none():
    text = "(Vide Lei nº 8.072)"
    anns = extract_annotations(text)
    assert anns[0].kind == "vide"
    assert anns[0].year is None


def test_status_revogado_dominates():
    text = "(Redação dada pela Lei nº 1, de 2000) (Revogado pela Lei nº 2, de 2010)"
    assert status_from_annotations(extract_annotations(text)) == VigenciaStatus.REVOGADO


def test_status_alterado_when_only_redacao():
    text = "(Redação dada pela Lei nº 13.964, de 2019)"
    assert status_from_annotations(extract_annotations(text)) == VigenciaStatus.ALTERADO


def test_status_vigente_when_no_annotations():
    assert status_from_annotations([]) == VigenciaStatus.VIGENTE


def test_extract_year_from_full_date_dd_mm_yyyy():
    # Real Planalto format: "(Redação dada pela Lei nº 7.209, de 11.7.1984)"
    text = "(Redação dada pela Lei nº 7.209, de 11.7.1984)"
    anns = extract_annotations(text)
    assert anns[0].kind == "redacao"
    assert anns[0].law_ref == "Lei nº 7.209"
    assert anns[0].year == 1984


def test_extract_year_from_ordinal_day_date():
    # Real Planalto format: "(Revogado pela Lei nº 9.268, de 1º.4.1996)"
    text = "(Revogado pela Lei nº 9.268, de 1º.4.1996)"
    anns = extract_annotations(text)
    assert anns[0].kind == "revogado"
    assert anns[0].year == 1996


def test_extract_annotation_with_embedded_crlf():
    # Real Planalto annotations contain embedded \r\n line breaks.
    text = "(Redação dada\r\npela Lei nº 7.209, de 11.7.1984)"
    anns = extract_annotations(text)
    assert anns[0].kind == "redacao"
    assert anns[0].law_ref == "Lei nº 7.209"
    assert anns[0].year == 1984
