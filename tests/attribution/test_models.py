from direito_dados.attribution.models import (
    Author,
    Authorship,
    from_json,
    parse_law_ref,
    to_json,
)


def test_parse_law_ref_lei():
    assert parse_law_ref("Lei nº 13.964", 2019) == (13964, 2019, "LEI")


def test_parse_law_ref_emenda_constitucional():
    assert parse_law_ref("Emenda Constitucional nº 45", 2004) == (45, 2004, "EMC")


def test_parse_law_ref_lei_complementar():
    assert parse_law_ref("Lei Complementar nº 95", 1998) == (95, 1998, "LEI-COMPLEMENTAR")


def test_parse_law_ref_strips_thousands_dots():
    assert parse_law_ref("Lei nº 13.964", 2019)[0] == 13964


def test_parse_law_ref_none_when_year_missing():
    assert parse_law_ref("Lei nº 13.964", None) is None


def test_parse_law_ref_none_when_type_unrecognized():
    assert parse_law_ref("Medida Provisória nº 2.187", 2001) is None


def test_parse_law_ref_none_for_garbage_label():
    assert parse_law_ref("", 2001) is None


def test_author_json_round_trip():
    author = Author(name="José Rocha", kind="DEPUTADO", party="PL", uf="BA")
    record = Authorship(
        law_ref="Lei nº 13.964",
        numero=13964,
        ano=2019,
        tipo="LEI",
        status="resolved",
        origin_bill="PL 10372/2018",
        origin_house="CD",
        authors=[author],
        source="senado:processo/7850496",
        note="",
    )
    envelope = to_json([record])
    assert envelope["records"][0]["authors"][0]["party"] == "PL"
    restored = from_json(envelope)
    assert restored == [record]


def test_to_json_from_json_round_trip_preserves_envelope_fields():
    record = Authorship(
        law_ref="Lei nº 11.340", numero=11340, ano=2006, tipo="LEI",
        status="no_parliamentary_author",
    )
    envelope = to_json([record], fetched_at="2026-07-11T00:00:00", source="senado+camara")
    assert envelope["fetched_at"] == "2026-07-11T00:00:00"
    assert envelope["source"] == "senado+camara"
    assert envelope["records"][0]["law_ref"] == "Lei nº 11.340"
    restored = from_json(envelope)
    assert restored == [record]
