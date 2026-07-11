"""Senado Federal "processo" API client — the primary attribution source.

`GET /processo?numeroNorma=&anoNorma=&tipoNorma=` is a reverse lookup: given
only a law's number/year/type it returns every legislative "processo" record
tied to that norm (originating bill, revising-house copy, veto message),
regardless of which house the bill started in. `GET /processo/{id}` then
returns the true origin bill number/house and author(s) of record. See the
attribution spike doc for the live validation this client is built on.
"""

import time

import requests

from direito_dados.attribution.models import Author, Authorship

_HEADERS = {
    "User-Agent": (
        "direito-dados-attribution/0.1 (educational project; "
        "contact: anderson@seaworthysoftware.com)"
    ),
    "Accept": "application/json",
}


class SenadoProcessoClient:
    """Thin, polite HTTP client over the Senado "processo" open-data API."""

    def __init__(
        self,
        base_url: str = "https://legis.senado.leg.br/dadosabertos",
        delay: float = 0.6,
        timeout: int = 30,
        retries: int = 3,
    ):
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.retries = retries

    def _get(self, path: str, params: dict | None = None) -> dict | list:
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
        raise RuntimeError(f"Senado API request failed: {path}") from last_error

    def lookup(self, numero: int, ano: int, tipo: str) -> list[dict]:
        return self._get(
            "/processo",
            params={"numeroNorma": numero, "anoNorma": ano, "tipoNorma": tipo},
        )

    def detail(self, processo_id: int) -> dict:
        return self._get(f"/processo/{processo_id}")

    def resolve(self, law_ref: str, numero: int, ano: int, tipo: str) -> Authorship:
        """Resolve `law_ref` to its origin bill and author(s) of record."""
        results = self.lookup(numero, ano, tipo)
        if not results:
            return Authorship(
                law_ref=law_ref, numero=numero, ano=ano, tipo=tipo,
                status="not_found",
            )

        record = _select_record(results)
        if record is None:
            return Authorship(
                law_ref=law_ref, numero=numero, ano=ano, tipo=tipo,
                status="not_found",
                note="lookup returned only veto records",
            )

        detail = self.detail(record["id"])
        authors = [
            Author(
                name=a.get("autor", ""),
                kind=a.get("siglaTipo", ""),
                party=a.get("siglaPartido", ""),
                uf=a.get("uf", ""),
            )
            for a in detail.get("autoriaIniciativa") or []
        ]
        status = "resolved" if authors else "no_parliamentary_author"
        return Authorship(
            law_ref=law_ref, numero=numero, ano=ano, tipo=tipo, status=status,
            origin_bill=detail.get("identificacaoProcessoInicial", ""),
            origin_house=detail.get("siglaCasaIniciadora", ""),
            authors=authors,
            source=f"senado:processo/{record['id']}",
        )


def _select_record(results: list[dict]) -> dict | None:
    """Pick the best `processo` record: prefer "Iniciadora", else the first
    non-veto record. Returns None when every record is a veto message."""
    non_veto = [r for r in results if not str(r.get("identificacao", "")).startswith("VET")]
    if not non_veto:
        return None
    for r in non_veto:
        if r.get("objetivo") == "Iniciadora":
            return r
    return non_veto[0]
