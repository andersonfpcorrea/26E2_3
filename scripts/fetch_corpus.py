"""Download all 9 criminal-microsystem norms into data/raw/."""

from direito_dados.corpus.fetch import download_norm
from direito_dados.corpus.registry import NORMS

RAW_DIR = "data/raw"


def main() -> None:
    for norm_id, spec in NORMS.items():
        path = download_norm(spec, RAW_DIR)
        print(f"{norm_id}: {path}")


if __name__ == "__main__":
    main()
