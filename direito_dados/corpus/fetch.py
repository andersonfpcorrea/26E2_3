"""Download Planalto consolidated texts and reduce HTML to plain text."""

from pathlib import Path

import requests
from bs4 import BeautifulSoup

from direito_dados.corpus.registry import NormSpec

_HEADERS = {"User-Agent": "direito-dados-research/0.1 (academic project)"}


def html_to_plain_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def download_norm(spec: NormSpec, raw_dir: str) -> str:
    response = requests.get(spec.source_url, headers=_HEADERS, timeout=60)
    response.raise_for_status()
    # Planalto consolidated pages are served as latin-1 (ISO-8859-1); trust
    # that over `apparent_encoding`, which can misdetect on these pages.
    response.encoding = "latin-1"
    plain = html_to_plain_text(response.text)
    out_path = Path(raw_dir, spec.filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(plain, encoding="utf-8")
    return str(out_path)
