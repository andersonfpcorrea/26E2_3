"""Tests for authorship analytics — pure, on hand-built records."""

from direito_dados.analytics.authorship import (
    amendments_by_origin,
    authors_by_party,
    top_authors,
)
from direito_dados.attribution.models import Author, Authorship


def _record(law_ref, ano, authors, origin_house="", status="resolved"):
    return Authorship(
        law_ref=law_ref, numero=1, ano=ano, tipo="LEI", status=status,
        origin_house=origin_house, authors=authors,
    )


def test_authors_by_party_counts_only_parliamentary_authors():
    records = [
        _record("Lei nº 1", 2020, [Author(name="A", kind="DEPUTADO", party="PL")]),
        _record("Lei nº 2", 2021, [Author(name="B", kind="SENADOR", party="PT")]),
        _record("Lei nº 3", 2022, [Author(name="C", kind="DEPUTADO", party="PL")]),
        _record("Lei nº 4", 2023, [Author(name="Presidência da República", kind="PRESIDENTE_REPUBLICA")]),
    ]
    result = authors_by_party(records)
    assert result == {"PL": 2, "PT": 1}


def test_amendments_by_origin_classifies_executive_commission_and_houses():
    records = [
        _record("Lei nº 1", 2020, [Author(name="Presidência", kind="PRESIDENTE_REPUBLICA")]),
        _record("Lei nº 2", 2021, [Author(name="CPMI", kind="COMISSAO")]),
        _record("Lei nº 3", 2022, [Author(name="A", kind="DEPUTADO")], origin_house="CD"),
        _record("Lei nº 4", 2023, [Author(name="B", kind="SENADOR")], origin_house="SF"),
        _record("Lei nº 5", 2024, [], origin_house=""),
    ]
    result = amendments_by_origin(records)
    assert result == {
        "Poder Executivo": 1, "Comissão": 1, "Câmara": 1, "Senado": 1, "outros": 1,
    }


def test_amendments_by_origin_ignores_unresolved_records():
    records = [_record("Lei nº 1", 2020, [], origin_house="CD", status="not_found")]
    assert amendments_by_origin(records) == {}


def test_top_authors_ranks_by_law_count_with_party_label():
    author_a = Author(name="A", kind="DEPUTADO", party="PL")
    records = [
        _record("Lei nº 1", 2020, [author_a]),
        _record("Lei nº 2", 2021, [author_a]),
        _record("Lei nº 3", 2022, [Author(name="B", kind="SENADOR", party="PT")]),
    ]
    ranked = top_authors(records, top=15)
    assert ranked[0] == ("A (PL)", 2)
    assert ranked[1] == ("B (PT)", 1)


def test_top_authors_respects_top_limit():
    records = [
        _record(f"Lei nº {i}", 2020, [Author(name=f"P{i}", kind="DEPUTADO", party="PL")])
        for i in range(5)
    ]
    assert len(top_authors(records, top=2)) == 2
