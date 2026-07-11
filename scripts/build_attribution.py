"""Batch-resolve origin bill + author(s) of record for every external norm
(law/emenda) that amends or revokes the corpus, writing the committed
dataset `data/attribution/authorship.json`.

For each distinct external norm found on the graph, resolves via the Senado
Federal "processo" reverse lookup (primary source), enriched with the full
Câmara dos Deputados signer list when Senado's mirror likely under-reports
co-authorship (see `direito_dados.attribution.camara.enrich_authorship`).
Every law gets a record with an explicit `status` — nothing is silently
dropped.

Usage:

    uv run python scripts/build_attribution.py                # full run
    uv run python scripts/build_attribution.py --limit 10      # smoke run
    uv run python scripts/build_attribution.py --refresh       # refetch all

Idempotent by default: an existing `authorship.json` is loaded first, and
already-`resolved` records are skipped (resume-friendly after a partial or
interrupted run); `--refresh` ignores the existing file and refetches
everything.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from direito_dados.attribution.camara import CamaraClient, enrich_authorship
from direito_dados.attribution.models import Authorship, from_json, parse_law_ref, to_json
from direito_dados.attribution.senado import SenadoProcessoClient
from direito_dados.corpus.loader import load_corpus
from direito_dados.graph.builder import build_graph
from direito_dados.graph.models import NodeKind, NormGraph

RAW_DIR = str(_repo_root / "data" / "raw")
OUTPUT_PATH = _repo_root / "data" / "attribution" / "authorship.json"
SOURCE_LABEL = "senado:processo (+camara:autores fallback)"


def distinct_external_norms(graph: NormGraph) -> list[tuple[str, int | None]]:
    """Every distinct (law_ref, ano) pair among the graph's external norm
    nodes, sorted deterministically for reproducible --limit smoke runs."""
    refs = {
        (node.label, node.attrs.get("year"))
        for node in graph.nodes_of_kind(NodeKind.NORM)
        if node.attrs.get("external")
    }
    return sorted(refs, key=lambda t: (t[0], t[1] if t[1] is not None else -1))


# parse_law_ref's "LEI-COMPLEMENTAR" tipo is the human-readable value stored
# on the record; the Senado API's tipoNorma query param expects its sigla,
# "LCP" (see /legislacao/tiposNorma). Not exercised by the current corpus
# (no Lei Complementar amends it), but kept correct per the design doc.
_SENADO_TIPO_NORMA = {"LEI-COMPLEMENTAR": "LCP"}


def resolve_one(
    law_ref: str, year: int | None, senado: SenadoProcessoClient | None,
    camara: CamaraClient | None,
) -> Authorship:
    """Resolve a single external norm to an `Authorship` record. Never
    raises: any Senado API failure is reported as `status="not_found"` with
    the error recorded in `note`, so a batch run is never aborted by one
    unreachable law."""
    parsed = parse_law_ref(law_ref, year)
    if parsed is None:
        return Authorship(
            law_ref=law_ref, numero=0, ano=year or 0, tipo="", status="skipped_type",
        )
    numero, ano, tipo = parsed
    api_tipo = _SENADO_TIPO_NORMA.get(tipo, tipo)
    try:
        record = senado.resolve(law_ref, numero, ano, api_tipo)
        if api_tipo != tipo:
            record = replace(record, tipo=tipo)
    except Exception as exc:
        return Authorship(
            law_ref=law_ref, numero=numero, ano=ano, tipo=tipo, status="not_found",
            note=str(exc),
        )
    if record.status == "resolved":
        record = enrich_authorship(record, camara)
    return record


def resolved_keys(records: list[Authorship]) -> set[tuple[str, int]]:
    """(law_ref, ano) keys already `resolved` in a previously written dataset."""
    return {(r.law_ref, r.ano) for r in records if r.status == "resolved"}


def coverage_table(records: list[Authorship]) -> str:
    """Human-readable coverage summary, by status and by tipo."""
    lines = ["Por status:"]
    by_status = Counter(r.status for r in records)
    for status, count in sorted(by_status.items()):
        lines.append(f"  {status:<24} {count:>4}")

    lines.append("Por tipo (resolvidos / total):")
    by_tipo_total: Counter = Counter()
    by_tipo_resolved: Counter = Counter()
    for r in records:
        tipo = r.tipo or "(sem tipo)"
        by_tipo_total[tipo] += 1
        if r.status == "resolved":
            by_tipo_resolved[tipo] += 1
    for tipo, total in sorted(by_tipo_total.items()):
        resolved = by_tipo_resolved[tipo]
        rate = (resolved / total * 100) if total else 0.0
        lines.append(f"  {tipo:<24} {resolved:>4}/{total:<4} ({rate:.1f}%)")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Processa apenas as N primeiras normas (smoke run).")
    parser.add_argument("--refresh", action="store_true", help="Ignora o dataset existente e refaz tudo.")
    parser.add_argument("--delay", type=float, default=0.6, help="Segundos entre requisições (padrão 0.6s).")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print("Carregando corpus e construindo o grafo normativo...")
    corpus = load_corpus(RAW_DIR)
    graph = build_graph(corpus)
    refs = distinct_external_norms(graph)
    if args.limit:
        refs = refs[: args.limit]
    total = len(refs)
    print(f"{total} normas externas distintas a resolver.")

    existing_records: list[Authorship] = []
    if OUTPUT_PATH.exists() and not args.refresh:
        existing_records = from_json(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")))
    already_resolved = resolved_keys(existing_records) if existing_records else set()
    existing_by_key = {(r.law_ref, r.ano): r for r in existing_records}

    senado = SenadoProcessoClient(delay=args.delay)
    camara = CamaraClient(delay=args.delay)

    records: list[Authorship] = []
    for i, (law_ref, year) in enumerate(refs, start=1):
        key = (law_ref, year)
        if key in already_resolved:
            records.append(existing_by_key[key])
            print(f"[{i}/{total}] SKIP (já resolvido)  {law_ref} ({year})")
            continue
        record = resolve_one(law_ref, year, senado, camara)
        records.append(record)
        tag = "OK  " if record.status == "resolved" else "FAIL"
        print(f"[{i}/{total}] {tag} {law_ref} ({year}) -> {record.status}")

    # Carry over any previously resolved law not present in this run's scope
    # (relevant only when --limit narrows the current pass).
    seen_keys = {(r.law_ref, r.ano) for r in records}
    for key, record in existing_by_key.items():
        if key not in seen_keys:
            records.append(record)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    envelope = to_json(records, fetched_at=fetched_at, source=SOURCE_LABEL)
    OUTPUT_PATH.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"\nGravado em {OUTPUT_PATH} ({len(records)} registros).")
    print()
    print(coverage_table(records))


if __name__ == "__main__":
    main()
