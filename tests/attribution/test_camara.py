"""Unit tests for the Câmara completeness fallback — no network, fixtures only."""

import json
from pathlib import Path

from direito_dados.attribution.camara import CamaraClient, enrich_authorship, parse_bill_id
from direito_dados.attribution.models import Author, Authorship

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_parse_bill_id():
    assert parse_bill_id("PL 10372/2018") == ("PL", 10372, 2018)


def test_parse_bill_id_pec():
    assert parse_bill_id("PEC 96/1992") == ("PEC", 96, 1992)


def test_parse_bill_id_invalid_returns_none():
    assert parse_bill_id("") is None
    assert parse_bill_id("not a bill") is None


def _client_with_fixtures() -> CamaraClient:
    client = CamaraClient()
    client._proposicao_id = lambda sigla, numero, ano: _load(
        "camara_proposicoes_pl10372"
    )["dados"][0]["id"]
    client._autores = lambda proposicao_id: _load("camara_autores_pl10372")["dados"]
    return client


def test_full_authors_returns_all_signers():
    client = _client_with_fixtures()
    authors = client.full_authors("PL 10372/2018")
    assert len(authors) == 11
    names = {a.name for a in authors}
    assert "José Rocha" in names
    assert "Rodrigo Garcia" in names
    assert all(a.kind == "DEPUTADO" for a in authors)
    assert all(a.party == "" for a in authors)


def test_full_authors_returns_empty_on_invalid_bill():
    client = CamaraClient()
    assert client.full_authors("garbage") == []


def _anticrime_record() -> Authorship:
    return Authorship(
        law_ref="Lei nº 13.964", numero=13964, ano=2019, tipo="LEI",
        status="resolved", origin_bill="PL 10372/2018", origin_house="CD",
        authors=[Author(name="José Rocha", kind="DEPUTADO", party="PL")],
        source="senado:processo/7850496",
    )


def test_enrich_authorship_replaces_with_full_camara_list():
    record = _anticrime_record()
    client = _client_with_fixtures()
    enriched = enrich_authorship(record, client)
    assert len(enriched.authors) == 11
    assert "coautoria completa via Câmara /autores" in enriched.note
    # original record is untouched (pure function)
    assert len(record.authors) == 1


def test_enrich_authorship_untouched_when_not_cd():
    record = Authorship(
        law_ref="Lei nº 12.015", numero=12015, ano=2009, tipo="LEI",
        status="resolved", origin_bill="PLS 253/2004", origin_house="SF",
        authors=[Author(name="CPMI", kind="COMISSAO")],
        source="senado:processo/1",
    )
    client = _client_with_fixtures()
    enriched = enrich_authorship(record, client)
    assert enriched == record


def test_enrich_authorship_untouched_when_not_single_deputy():
    record = Authorship(
        law_ref="Lei nº 11.340", numero=11340, ano=2006, tipo="LEI",
        status="resolved", origin_bill="PL 4559/2004", origin_house="CD",
        authors=[Author(name="Presidência da República", kind="PRESIDENTE_REPUBLICA")],
        source="senado:processo/1",
    )
    client = _client_with_fixtures()
    enriched = enrich_authorship(record, client)
    assert enriched == record


def test_enrich_authorship_untouched_on_camara_failure():
    record = _anticrime_record()
    client = CamaraClient()  # no fixtures wired; real network call would fail/return []
    client.full_authors = lambda bill: []
    enriched = enrich_authorship(record, client)
    assert enriched == record
