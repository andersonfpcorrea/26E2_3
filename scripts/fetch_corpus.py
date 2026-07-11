"""Download all 9 criminal-microsystem norms into data/raw/.

Run via ``make data`` (or ``uv run python scripts/fetch_corpus.py``).
A failing norm is reported and skipped rather than aborting the whole run.
"""

import sys
import time
from pathlib import Path

# Fallback for running without an installed package (plain `python scripts/fetch_corpus.py`).
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from direito_dados.corpus.fetch import download_norm
from direito_dados.corpus.registry import NORMS

RAW_DIR = "data/raw"
POLITE_DELAY = 1.5  # seconds between requests


def main() -> None:
    failures: list[str] = []
    for norm_id, spec in NORMS.items():
        try:
            path = download_norm(spec, RAW_DIR)
            print(f"OK   {norm_id}: {path}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append(norm_id)
            print(f"FAIL {norm_id}: {exc}")
        time.sleep(POLITE_DELAY)
    total = len(NORMS)
    print(f"\nDone: {total - len(failures)}/{total} downloaded.")
    if failures:
        print(f"Failed: {', '.join(failures)} (re-run to retry)")


if __name__ == "__main__":
    main()
