"""Unit tests for the pure helpers in scripts/build_attribution.py — no network.

Imports the script as a module (it lives outside the direito_dados package,
like the other batch scripts under scripts/).
"""

import importlib.util
import sys
from pathlib import Path

from direito_dados.attribution.models import Author, Authorship
from direito_dados.graph.models import Node, NodeKind, NormGraph

_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "build_attribution.py"
_spec = importlib.util.spec_from_file_location("build_attribution", _SCRIPT_PATH)
build_attribution = importlib.util.module_from_spec(_spec)
sys.modules["build_attribution"] = build_attribution
_spec.loader.exec_module(build_attribution)


def _graph_with_externals() -> NormGraph:
    g = NormGraph()
    g.add_node(Node(id="CP", kind=NodeKind.NORM, label="Código Penal", domain="penal"))
    g.add_node(Node(
        id="ext:Lei_nº_13.964;2019", kind=NodeKind.NORM, label="Lei nº 13.964",
        attrs={"external": True, "year": 2019},
    ))
    g.add_node(Node(
        id="ext:Emenda_Constitucional_nº_45;2004", kind=NodeKind.NORM,
        label="Emenda Constitucional nº 45", attrs={"external": True, "year": 2004},
    ))
    g.add_node(Node(
        id="ext:Medida_Provisória_nº_1;2001", kind=NodeKind.NORM,
        label="Medida Provisória nº 1", attrs={"external": True, "year": 2001},
    ))
    return g


def test_distinct_external_norms_excludes_internal_nodes():
    refs = build_attribution.distinct_external_norms(_graph_with_externals())
    assert ("Código Penal", None) not in refs
    assert ("Lei nº 13.964", 2019) in refs
    assert ("Emenda Constitucional nº 45", 2004) in refs
    assert len(refs) == 3


def test_distinct_external_norms_is_deterministically_sorted():
    refs = build_attribution.distinct_external_norms(_graph_with_externals())
    assert refs == sorted(refs)


def test_resolve_one_skipped_type_for_unparseable_label():
    record = build_attribution.resolve_one("Medida Provisória nº 1", 2001, senado=None, camara=None)
    assert record.status == "skipped_type"
    assert record.law_ref == "Medida Provisória nº 1"


def test_resolve_one_skipped_type_when_year_missing():
    record = build_attribution.resolve_one("Lei nº 1", None, senado=None, camara=None)
    assert record.status == "skipped_type"


class _FakeSenado:
    def resolve(self, law_ref, numero, ano, tipo):
        return Authorship(
            law_ref=law_ref, numero=numero, ano=ano, tipo=tipo, status="resolved",
            origin_bill="PL 1/2018", origin_house="CD",
            authors=[Author(name="Fulano", kind="DEPUTADO", party="XX")],
            source="senado:processo/1",
        )


class _FakeCamara:
    def full_authors(self, bill):
        return [
            Author(name="Fulano", kind="DEPUTADO"),
            Author(name="Sicrano", kind="DEPUTADO"),
        ]


def test_resolve_one_resolves_and_enriches_via_senado_and_camara():
    record = build_attribution.resolve_one(
        "Lei nº 13.964", 2019, senado=_FakeSenado(), camara=_FakeCamara(),
    )
    assert record.status == "resolved"
    assert len(record.authors) == 2  # enriched from 1 -> 2 via the fake Câmara client
    assert "coautoria completa" in record.note


class _FailingSenado:
    def resolve(self, law_ref, numero, ano, tipo):
        raise RuntimeError("Senado API request failed")


class _RecordingSenado:
    """Captures the tipoNorma actually sent, to verify the LCP mapping."""

    def __init__(self):
        self.seen_tipo = None

    def resolve(self, law_ref, numero, ano, tipo):
        self.seen_tipo = tipo
        return Authorship(law_ref=law_ref, numero=numero, ano=ano, tipo=tipo, status="not_found")


def test_resolve_one_maps_lei_complementar_to_lcp_for_senado_but_keeps_record_tipo():
    senado = _RecordingSenado()
    record = build_attribution.resolve_one(
        "Lei Complementar nº 95", 1998, senado=senado, camara=_FakeCamara(),
    )
    assert senado.seen_tipo == "LCP"
    assert record.tipo == "LEI-COMPLEMENTAR"


def test_resolve_one_reports_not_found_on_senado_failure():
    record = build_attribution.resolve_one(
        "Lei nº 1", 2020, senado=_FailingSenado(), camara=_FakeCamara(),
    )
    assert record.status == "not_found"
    assert "Senado API request failed" in record.note


def test_coverage_table_groups_by_status_and_tipo():
    records = [
        Authorship(law_ref="Lei nº 1", numero=1, ano=2020, tipo="LEI", status="resolved"),
        Authorship(law_ref="Lei nº 2", numero=2, ano=2020, tipo="LEI", status="not_found"),
        Authorship(law_ref="EC nº 1", numero=1, ano=2020, tipo="EMC", status="resolved"),
    ]
    table = build_attribution.coverage_table(records)
    assert "LEI" in table
    assert "EMC" in table
    assert "resolved" in table
    assert "not_found" in table


def test_merge_existing_skips_only_resolved_records():
    existing = [
        Authorship(law_ref="Lei nº 1", numero=1, ano=2020, tipo="LEI", status="resolved"),
        Authorship(law_ref="Lei nº 2", numero=2, ano=2020, tipo="LEI", status="not_found"),
    ]
    done = build_attribution.resolved_keys(existing)
    assert ("Lei nº 1", 2020) in done
    assert ("Lei nº 2", 2020) not in done
