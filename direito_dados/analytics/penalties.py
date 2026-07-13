"""Extract structured penalties from article texts.

Planalto penalty clauses follow the pattern ``Pena - reclusão, de X a Y anos``
with the bounds written as digits ("de 2 (dois) a 6 (seis) anos"), as words
("de um a quatro anos"), or mixed. Extracting them into (kind, min, max)
makes aggregate questions ("qual a maior pena?") computable deterministically
instead of guessed by an LLM from a handful of retrieved fragments.
"""

import re
from dataclasses import dataclass

from direito_dados.corpus.loader import Corpus

_WORDS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
    "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
}

_NUM = r"(?:\d+|" + "|".join(_WORDS) + r")"

_UNIT = r"(anos?|meses|mês)"

_PENALTY_RE = re.compile(
    r"(?i)(reclusão|detenção|prisão simples)\s*,?\s*"
    r"de\s+(" + _NUM + r")\s*(?:\([^)]{0,30}\))?\s*" + _UNIT + r"?\s*"
    r"(?:a|até)\s+(" + _NUM + r")\s*(?:\([^)]{0,30}\))?\s*" + _UNIT
)


@dataclass(frozen=True)
class Penalty:
    kind: str
    min_months: int
    max_months: int
    excerpt: str


def _to_number(token: str) -> int:
    token = token.strip().lower()
    return int(token) if token.isdigit() else _WORDS[token]


def extract_penalties(text: str) -> list[Penalty]:
    """All penalty ranges stated in an article's text (caput and paragraphs)."""
    penalties: list[Penalty] = []
    for m in _PENALTY_RE.finditer(text):
        kind, lo_tok, lo_unit, hi_tok, hi_unit = m.groups()
        hi_factor = 12 if hi_unit.lower().startswith("ano") else 1
        # The first bound may carry its own unit ("de três meses a um ano");
        # otherwise it shares the closing unit.
        lo_factor = (12 if lo_unit.lower().startswith("ano") else 1) if lo_unit else hi_factor
        lo, hi = _to_number(lo_tok) * lo_factor, _to_number(hi_tok) * hi_factor
        if lo > hi:  # malformed/inverted range — skip rather than mislead
            continue
        excerpt = " ".join(m.group(0).split())
        penalties.append(Penalty(kind=kind.lower(), min_months=lo, max_months=hi,
                                 excerpt=excerpt))
    return penalties


def top_penalties(corpus: Corpus, n: int = 5, lowest: bool = False):
    """Articles ranked by their harshest stated penalty (or mildest, `lowest`).

    Returns [(citation, chunk_id, Penalty)] over in-force articles only.
    """
    ranked = []
    for norm in corpus.norms:
        for art in norm.in_force_articles() if hasattr(norm, "in_force_articles") else norm.articles:
            if art.status.value == "revogado":
                continue
            pens = extract_penalties(art.text)
            if not pens:
                continue
            best = min(pens, key=lambda p: p.min_months) if lowest else max(pens, key=lambda p: p.max_months)
            ranked.append((art.citation, f"{norm.id}:art{art.number}", best))
    key = (lambda t: t[2].min_months) if lowest else (lambda t: -t[2].max_months)
    return sorted(ranked, key=key)[:n]


def format_months(months: int) -> str:
    if months % 12 == 0:
        years = months // 12
        return f"{years} ano{'s' if years != 1 else ''}"
    return f"{months} meses"
