"""Câmara dos Deputados Dados Abertos API v2 — completeness fallback.

Senado's `autoriaIniciativa` sometimes lists only the primary signer of a
Câmara-origin bill (confirmed for the 11-deputy anticrime package, which the
Senado mirror reports as a single author). `/proposicoes/{id}/autores` is
the completeness source of truth for co-authorship; this module is used only
as a best-effort enrichment step, never as the primary attribution source
(no reverse "law -> bill" lookup exists on the Câmara side — see the
attribution spike doc).
"""

import re
import time
from dataclasses import replace

import requests

from direito_dados.attribution.models import Author, Authorship

_HEADERS = {
    "User-Agent": (
        "direito-dados-attribution/0.1 (educational project; "
        "contact: anderson@seaworthysoftware.com)"
    ),
    "Accept": "application/json",
}

_BILL_ID_RE = re.compile(r"^([A-Z]+)\s+(\d+)/(\d{4})$")

# Câmara's autores "tipo" field ("Deputado(a)") normalized to the same
# siglaTipo vocabulary Senado's autoriaIniciativa uses ("DEPUTADO"), so
# downstream analytics/enrichment don't need to know which source a record
# came from.
_KIND_NORMALIZATION = {"deputado(a)": "DEPUTADO"}


def parse_bill_id(s: str) -> tuple[str, int, int] | None:
    """Parse a bill identification string, e.g. "PL 10372/2018" -> ("PL", 10372, 2018)."""
    match = _BILL_ID_RE.match(s.strip()) if s else None
    if match is None:
        return None
    sigla, numero, ano = match.groups()
    return sigla, int(numero), int(ano)


class CamaraClient:
    """Thin, polite HTTP client over the Câmara dos Deputados open-data API."""

    def __init__(
        self,
        base_url: str = "https://dadosabertos.camara.leg.br/api/v2",
        delay: float = 0.6,
        timeout: int = 30,
        retries: int = 3,
    ):
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.retries = retries

    def _get(self, path: str, params: dict | None = None) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    f"{self.base_url}{path}", params=params,
                    headers=_HEADERS, timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
            time.sleep(self.delay * (attempt + 1))
        raise RuntimeError(f"Câmara API request failed: {path}") from last_error

    def _proposicao_id(self, sigla: str, numero: int, ano: int) -> int | None:
        data = self._get(
            "/proposicoes", params={"siglaTipo": sigla, "numero": numero, "ano": ano},
        )
        items = data.get("dados") or []
        return items[0]["id"] if items else None

    def _autores(self, proposicao_id: int) -> list[dict]:
        return self._get(f"/proposicoes/{proposicao_id}/autores").get("dados") or []

    def full_authors(self, bill: str) -> list[Author]:
        """Return every signer of `bill` (e.g. "PL 10372/2018"). Best-effort:
        returns [] on an unparseable bill id or any API failure."""
        parsed = parse_bill_id(bill)
        if parsed is None:
            return []
        sigla, numero, ano = parsed
        try:
            proposicao_id = self._proposicao_id(sigla, numero, ano)
            if proposicao_id is None:
                return []
            autores = self._autores(proposicao_id)
        except Exception:
            return []
        return [
            Author(
                name=a.get("nome", ""),
                kind=_KIND_NORMALIZATION.get(a.get("tipo", "").lower(), a.get("tipo", "")),
                party="",
            )
            for a in autores
        ]


def enrich_authorship(record: Authorship, camara: CamaraClient) -> Authorship:
    """Replace `record.authors` with the full Câmara signer list when Senado's
    mirror likely under-reports co-authorship: a Câmara-origin bill
    (`origin_house == "CD"`) whose Senado-derived authors are exactly one
    DEPUTADO. Returns `record` unchanged in every other case, including any
    Câmara API failure (best-effort enrichment)."""
    if record.origin_house != "CD":
        return record
    if not (len(record.authors) == 1 and record.authors[0].kind == "DEPUTADO"):
        return record

    full = camara.full_authors(record.origin_bill)
    if len(full) <= len(record.authors):
        return record

    return replace(
        record, authors=full,
        note=(record.note + " " if record.note else "")
        + "coautoria completa via Câmara /autores",
    )
