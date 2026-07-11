"""Data models for the attribution layer and law-reference parsing.

`Author`/`Authorship` are the unit resolved per external norm (see
`direito_dados.attribution.senado` and `.camara`); `parse_law_ref` turns the
Planalto-style label already present on the graph's external norm nodes
(e.g. ``"Lei nº 13.964"``) into the `(numero, ano, tipo)` triple used to query
Congress's own open-data reverse lookup.
"""

import re
from dataclasses import asdict, dataclass, field

_TIPO_BY_PREFIX = {
    "lei complementar": "LEI-COMPLEMENTAR",
    "emenda constitucional": "EMC",
    "lei": "LEI",
}

# Ordered longest-prefix-first so "Lei Complementar" is not swallowed by "Lei".
_LAW_REF_RE = re.compile(
    r"^(?P<prefix>Lei Complementar|Emenda Constitucional|Lei)\s+n[ºo]\s*(?P<numero>[\d.]+)$",
    re.IGNORECASE,
)


def parse_law_ref(label: str, year: int | None) -> tuple[int, int, str] | None:
    """Parse a Planalto-style law reference label into `(numero, ano, tipo)`.

    Returns None when `year` is missing or the reference type is not one of
    the recognized ordinary/complementary law or constitutional amendment
    forms (e.g. "Medida Provisória", "Decreto-Lei" — out of scope for now).
    """
    if year is None or not label:
        return None
    match = _LAW_REF_RE.match(label.strip())
    if match is None:
        return None
    tipo = _TIPO_BY_PREFIX[match.group("prefix").lower()]
    numero = int(match.group("numero").replace(".", ""))
    return numero, year, tipo


@dataclass(frozen=True)
class Author:
    """An author of record, individual or institutional."""

    name: str
    kind: str
    party: str = ""
    uf: str = ""


@dataclass
class Authorship:
    """Resolved (or attempted) origin-bill + authorship for one external norm."""

    law_ref: str
    numero: int
    ano: int
    tipo: str
    status: str
    origin_bill: str = ""
    origin_house: str = ""
    authors: list[Author] = field(default_factory=list)
    source: str = ""
    note: str = ""


def to_json(records: list[Authorship], fetched_at: str = "", source: str = "") -> dict:
    """Serialize records into the committed dataset envelope.

    `fetched_at` is supplied by the caller (e.g. the batch script's run
    timestamp) rather than computed here, keeping this function pure.
    """
    return {
        "fetched_at": fetched_at,
        "source": source,
        "records": [
            {**asdict(r), "authors": [asdict(a) for a in r.authors]}
            for r in records
        ],
    }


def from_json(data: dict) -> list[Authorship]:
    """Deserialize the committed dataset envelope back into `Authorship` records."""
    records = []
    for raw in data.get("records", []):
        authors = [Author(**a) for a in raw.get("authors", [])]
        records.append(Authorship(**{**raw, "authors": authors}))
    return records
