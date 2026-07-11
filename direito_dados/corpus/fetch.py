"""Download Planalto consolidated texts and reduce HTML to plain text."""

import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from direito_dados.corpus.registry import NormSpec

# Planalto rejects non-browser User-Agents (connection reset), so present a
# browser-like agent. This is a polite, low-volume fetch of public-domain law.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def decode_planalto(content: bytes) -> str:
    """Decode a Planalto page. Most are latin-1, but some older FrontPage pages
    (e.g. Lei Maria da Penha) are UTF-16 with a BOM — detect and honour it."""
    if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
        # The "utf-16" codec reads the BOM, picks endianness, and strips the BOM.
        return content.decode("utf-16", errors="replace")
    if content[:3] == b"\xef\xbb\xbf":
        return content.decode("utf-8-sig", errors="replace")
    return content.decode("latin-1", errors="replace")


def html_to_plain_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def download_norm(spec: NormSpec, raw_dir: str, retries: int = 3,
                  backoff: float = 2.0) -> str:
    """Fetch a norm's consolidated text, retrying on transient network resets."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(spec.source_url, headers=_HEADERS, timeout=60)
            response.raise_for_status()
            # Decode from raw bytes: most pages are latin-1, some are UTF-16 (BOM).
            plain = html_to_plain_text(decode_planalto(response.content))
            out_path = Path(raw_dir, spec.filename)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(plain, encoding="utf-8")
            return str(out_path)
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Failed to download {spec.id} after {retries} attempts") from last_error
