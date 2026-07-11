"""Analytics over resolved authorship-of-record: party breakdown, origin
(Poder Executivo/Câmara/Senado/Comissão), and most-prolific authors.

All functions are pure and operate only on `resolved` records — the
candidate-transparency framing ("autoria de registro") lives in the app
tab, not here.
"""

from collections import Counter

from direito_dados.attribution.models import Authorship

_PARLIAMENTARY_KINDS = {"DEPUTADO", "SENADOR"}
_EXECUTIVE_KINDS = {"PRESIDENTE_REPUBLICA"}
# Senado's siglaTipo vocabulary for collegiate authors includes variants like
# COMISSAO_CONGRESSO (observed live for CPMI-origin laws, e.g. Lei 12.015/2009),
# so commission-ness is matched by prefix, not exact value.
_COMMISSION_PREFIXES = ("COMISSAO", "CPMI", "ORGAO_COLEGIADO")


def authors_by_party(records: list[Authorship]) -> dict[str, int]:
    """Count of (author, law) pairs by party, parliamentary authors only."""
    counts: Counter[str] = Counter()
    for record in records:
        if record.status != "resolved":
            continue
        for author in record.authors:
            if author.kind in _PARLIAMENTARY_KINDS and author.party:
                counts[author.party] += 1
    return dict(counts)


def _origin_category(record: Authorship) -> str:
    kinds = {a.kind for a in record.authors}
    if kinds & _EXECUTIVE_KINDS:
        return "Poder Executivo"
    if any(k.startswith(_COMMISSION_PREFIXES) for k in kinds):
        return "Comissão"
    if record.origin_house == "CD":
        return "Câmara"
    if record.origin_house == "SF":
        return "Senado"
    return "outros"


def amendments_by_origin(records: list[Authorship]) -> dict[str, int]:
    """Count of resolved laws by origin category."""
    counts: Counter[str] = Counter()
    for record in records:
        if record.status != "resolved":
            continue
        counts[_origin_category(record)] += 1
    return dict(counts)


def top_authors(records: list[Authorship], top: int = 15) -> list[tuple[str, int]]:
    """The most prolific authors of record, labeled "Nome (Partido)" when a
    party is known, ranked by number of laws authored."""
    counts: Counter[str] = Counter()
    for record in records:
        if record.status != "resolved":
            continue
        for author in record.authors:
            label = f"{author.name} ({author.party})" if author.party else author.name
            counts[label] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top]
