from direito_dados.graph.models import (
    Edge, EdgeKind, NormGraph, Provenance, VerificationState,
)
from direito_dados.analytics.timeline import (
    amendment_events, amendments_by_year, amendments_by_decade, amendments_per_norm,
)

def _prov():
    return Provenance(source="planalto:CP", extracted_by="annotation-parser")

def _graph():
    g = NormGraph()
    def edge(kind, dst, year, law="Lei nº 1"):
        return Edge(kind=kind, src=f"ext:{law}", dst=dst, provenance=_prov(),
                    verification_state=VerificationState.VERIFIED,
                    attrs={"law_ref": law, "year": year})
    g.add_edge(edge(EdgeKind.AMENDS, "CP:art121", 1984))
    g.add_edge(edge(EdgeKind.AMENDS, "CP:art155", 2018))
    g.add_edge(edge(EdgeKind.REVOKES, "CP:art240", 2005))
    g.add_edge(edge(EdgeKind.AMENDS, "CPP:art10", None))   # unknown year
    return g

def test_amendment_events_carry_year_kind_norm():
    evs = amendment_events(_graph())
    assert len(evs) == 4
    art155 = next(e for e in evs if e["target"] == "CP:art155")
    assert art155["year"] == 2018 and art155["kind"] == "amends" and art155["norm_id"] == "CP"

def test_by_year_skips_unknown():
    by_year = amendments_by_year(_graph())
    assert by_year == {1984: 1, 2018: 1, 2005: 1}   # the None is skipped

def test_by_decade_buckets():
    by_dec = amendments_by_decade(_graph())
    assert by_dec == {1980: 1, 2010: 1, 2000: 1}

def test_per_norm_counts():
    per = amendments_per_norm(_graph())
    assert per == {"CP": 3, "CPP": 1}
