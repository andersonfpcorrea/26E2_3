"""Parsing of Planalto inline vigência annotations.

Planalto consolidated texts annotate every changed provision with
parentheticals such as ``(Redação dada pela Lei nº 13.964, de 2019)`` or
``(Revogado pela Lei nº 11.106, de 2005)``. Real Planalto pages also date
annotations with a full ``DD.MM.YYYY`` (or ordinal ``1º.M.YYYY``) form, e.g.
``(Redação dada pela Lei nº 7.209, de 11.7.1984)`` or
``(Revogado pela Lei nº 9.268, de 1º.4.1996)``, in addition to the bare-year
``de 2019`` form. This module turns those into structured ``Annotation``
objects and derives a ``VigenciaStatus``.
"""

import re

from direito_dados.corpus.models import Annotation, VigenciaStatus

_KIND_BY_KEYWORD = {
    "redação dada": "redacao",
    "redacao dada": "redacao",
    "revogado": "revogado",
    "revogada": "revogado",
    "incluído": "incluido",
    "incluido": "incluido",
    "renumerado": "renumerado",
    "vide": "vide",
}

# Matches the annotation body inside parentheses, capturing the kind keyword,
# the law reference (Lei / Lei Complementar / Decreto-Lei / Medida Provisória /
# Emenda Constitucional nº X) and optional year. The law reference (and year)
# are themselves optional, since a bare "(Revogado)" / "(Revogado.)" with no
# "pela Lei..." clause is valid and must still be captured — this matters
# because a fully-revoked-article caput with no law reference must not be
# silently dropped. The year may appear as a bare 4-digit year ("de 2019") or
# as the trailing year of a full date, optionally with an ordinal day marker
# ("de 11.7.1984", "de 1º.4.1996"). `[^)]` intentionally spans embedded
# `\r\n` line breaks found in real Planalto annotations.
_ANNOTATION_RE = re.compile(
    r"\(\s*"
    r"(?P<kind>Reda[çc][ãa]o dada|Revogad[oa]|Inclu[íi]do|Renumerado|Vide)"
    r"(?:"
    r"[^)]*?"
    r"(?P<lawref>(?:Lei Complementar|Medida Provis[óo]ria|Lei|Decreto-Lei|Emenda Constitucional)"
    r"\s+n[ºo]\s*[\d.]+)"
    r"(?:[^)]*?de\s+(?:\d{1,2}º?\.\d{1,2}\.)?(?P<year>\d{4}))?"
    r")?"
    r"[^)]*\)",
    re.IGNORECASE,
)


def _normalize_kind(raw: str) -> str:
    key = raw.strip().lower()
    for keyword, kind in _KIND_BY_KEYWORD.items():
        if key.startswith(keyword):
            return kind
    return key


def _normalize_lawref(raw: str) -> str:
    # Collapse internal whitespace and standardize "nº".
    ref = re.sub(r"\s+", " ", raw).strip()
    return ref.replace("no ", "nº ").replace("No ", "nº ")


def extract_annotations(text: str) -> list[Annotation]:
    annotations: list[Annotation] = []
    for match in _ANNOTATION_RE.finditer(text):
        year_str = match.group("year")
        lawref = match.group("lawref")
        annotations.append(
            Annotation(
                kind=_normalize_kind(match.group("kind")),
                law_ref=_normalize_lawref(lawref) if lawref else "",
                year=int(year_str) if year_str else None,
            )
        )
    return annotations


def status_from_annotations(annotations: list[Annotation]) -> VigenciaStatus:
    kinds = {a.kind for a in annotations}
    if "revogado" in kinds:
        return VigenciaStatus.REVOGADO
    if kinds & {"redacao", "incluido", "renumerado"}:
        return VigenciaStatus.ALTERADO
    return VigenciaStatus.VIGENTE


def article_status(caput: str, annotations: list[Annotation]) -> VigenciaStatus:
    """Article-level vigência: REVOGADO only if the caput itself is revoked;
    ALTERADO if the article was otherwise touched; else VIGENTE."""
    if any(a.kind == "revogado" for a in extract_annotations(caput)):
        return VigenciaStatus.REVOGADO
    if annotations:
        return VigenciaStatus.ALTERADO
    return VigenciaStatus.VIGENTE
