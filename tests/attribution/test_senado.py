"""Unit tests for SenadoProcessoClient.resolve — pure normalization, no network.

`lookup`/`detail` are monkeypatched to return the fixtures captured live in
tests/attribution/fixtures/ (see the attribution spike doc for provenance).
"""

import json
from pathlib import Path

import pytest

from direito_dados.attribution.senado import SenadoProcessoClient

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _client(lookup_fixture: str, detail_fixture: str) -> SenadoProcessoClient:
    client = SenadoProcessoClient()
    client.lookup = lambda numero, ano, tipo: _load(lookup_fixture)
    client.detail = lambda processo_id: _load(detail_fixture)
    return client


def test_resolve_anticrime():
    client = _client("anticrime_lookup", "anticrime_detail")
    record = client.resolve("Lei nº 13.964", 13964, 2019, "LEI")
    assert record.status == "resolved"
    assert record.origin_bill == "PL 10372/2018"
    assert record.origin_house == "CD"
    assert record.source == "senado:processo/7850496"
    assert len(record.authors) == 1
    author = record.authors[0]
    assert author.name == "José Rocha"
    assert author.kind == "DEPUTADO"
    assert author.party == "PL"


def test_resolve_maria_da_penha_institutional():
    client = _client("maria_da_penha_lookup", "maria_da_penha_detail")
    record = client.resolve("Lei nº 11.340", 11340, 2006, "LEI")
    assert record.status == "resolved"
    assert record.origin_bill == "PL 4559/2004"
    assert record.origin_house == "CD"
    assert len(record.authors) == 1
    assert record.authors[0].name == "Presidência da República"
    assert record.authors[0].kind == "PRESIDENTE_REPUBLICA"
    assert record.authors[0].party == ""


def test_resolve_ec45_prefers_deputy_author():
    client = _client("ec45_lookup", "ec45_detail")
    record = client.resolve("Emenda Constitucional nº 45", 45, 2004, "EMC")
    assert record.status == "resolved"
    assert record.origin_bill == "PEC 96/1992"
    assert record.authors[0].name == "Hélio Bicudo"


def test_resolve_not_found_when_lookup_empty():
    client = SenadoProcessoClient()
    client.lookup = lambda numero, ano, tipo: []
    record = client.resolve("Lei nº 99.999", 99999, 2099, "LEI")
    assert record.status == "not_found"
    assert record.authors == []
    assert record.numero == 99999
    assert record.ano == 2099
    assert record.tipo == "LEI"


def test_resolve_no_parliamentary_author_when_autoria_empty():
    client = SenadoProcessoClient()
    client.lookup = lambda numero, ano, tipo: [
        {"id": 1, "identificacao": "PL 1/2020", "objetivo": "Iniciadora"}
    ]
    client.detail = lambda processo_id: {
        "identificacaoProcessoInicial": "PL 1/2020",
        "siglaCasaIniciadora": "CD",
        "autoriaIniciativa": [],
    }
    record = client.resolve("Lei nº 1", 1, 2020, "LEI")
    assert record.status == "no_parliamentary_author"
    assert record.origin_bill == "PL 1/2020"


def test_resolve_skips_veto_records_and_prefers_iniciadora():
    client = SenadoProcessoClient()
    calls = []
    client.lookup = lambda numero, ano, tipo: [
        {"id": 1, "identificacao": "VET 1/2020", "objetivo": ""},
        {"id": 2, "identificacao": "PL 2/2020", "objetivo": "Iniciadora"},
        {"id": 3, "identificacao": "PL 3/2020", "objetivo": "Revisora"},
    ]

    def detail(processo_id):
        calls.append(processo_id)
        return {
            "identificacaoProcessoInicial": "PL 2/2020",
            "siglaCasaIniciadora": "CD",
            "autoriaIniciativa": [{"autor": "Fulano", "siglaTipo": "DEPUTADO"}],
        }

    client.detail = detail
    record = client.resolve("Lei nº 2", 2, 2020, "LEI")
    assert calls == [2]
    assert record.source == "senado:processo/2"
