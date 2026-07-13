"""Build (or reuse) the persisted full-corpus semantic index in data/index/.

Run via ``make run`` (provisioning step) or directly:

    uv run python scripts/build_index.py

Embedding all articles takes ~2 minutes on CPU the first time (a progress bar
is shown); afterwards the persisted index is reused and this exits in seconds.
"""

import sys
import time
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from direito_dados.corpus import load_corpus
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex, persisted_matches

RAW_DIR = str(_repo_root / "data" / "raw")
INDEX_DIR = str(_repo_root / "data" / "index")


def main() -> None:
    corpus = load_corpus(RAW_DIR)
    chunks = chunk_corpus(corpus)
    if persisted_matches(chunks, INDEX_DIR):
        print(f"  Índice semântico: presente ({len(chunks)} dispositivos, reutilizado).")
        return
    print(f"  Construindo o índice semântico das 9 normas ({len(chunks)} dispositivos).")
    print("  Isso acontece UMA vez (~2 min em CPU); as próximas execuções reutilizam o índice.")
    start = time.time()
    VectorIndex.open_or_build(chunks, E5Embedder(show_progress=True), INDEX_DIR)
    print(f"  Índice pronto em {time.time() - start:.0f}s (persistido em data/index/).")


if __name__ == "__main__":
    main()
