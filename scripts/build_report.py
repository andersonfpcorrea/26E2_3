"""Render the Portuguese technical report (Markdown) to the required PDF.

Pure-Python toolchain (``markdown`` + ``xhtml2pdf``) so the build runs on any OS
without pandoc, LaTeX, or system libraries. Installed via the ``report`` extra:

    .venv/bin/pip install -e ".[report]"
    .venv/bin/python scripts/build_report.py

Relative image paths in the Markdown (``figures/...``) are resolved against the
report directory through a pisa ``link_callback``.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "report"
SOURCE_MD = REPORT_DIR / "relatorio.md"
OUTPUT_PDF = (
    REPORT_DIR
    / "anderson_correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf"
)

CSS = """
@page { size: a4 portrait; margin: 1.8cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 19pt; color: #0a2540; margin-top: 0.2cm; }
h2 { font-size: 14pt; color: #0a2540; border-bottom: 1px solid #c8d2e0;
     padding-bottom: 3px; margin-top: 0.7cm; }
h3 { font-size: 12pt; color: #14457a; margin-top: 0.5cm; }
p, li { text-align: justify; }
code { font-family: Courier, monospace; background: #f2f4f7; font-size: 9.5pt; }
pre { background: #f2f4f7; padding: 8px; font-size: 9pt; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5pt; }
th, td { border: 1px solid #b8c2d0; padding: 4px 7px; }
th { background: #e8edf4; }
img { width: 440px; margin: 6px 0; }
hr { border: none; border-top: 1px solid #d0d7e2; margin: 0.5cm 0; }
blockquote { border-left: 3px solid #a44a3f; margin: 6px 0; padding: 2px 12px;
             color: #3a3a3a; background: #f7f2f0; }
"""


def link_callback(uri: str, _rel: str) -> str:
    """Resolve relative image URIs against the report directory for pisa."""
    if uri.startswith(("http://", "https://", "data:")):
        return uri
    resolved = (REPORT_DIR / uri).resolve()
    return str(resolved)


def build() -> None:
    """Convert the Markdown report into the deliverable PDF."""
    body = markdown.markdown(
        SOURCE_MD.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    # xhtml2pdf honors the img width attribute more reliably than CSS max-width.
    body = re.sub(r"<img ", '<img width="440" ', body)
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

    with OUTPUT_PDF.open("wb") as handle:
        result = pisa.CreatePDF(
            html, dest=handle, link_callback=link_callback, encoding="utf-8"
        )
    if result.err:
        raise RuntimeError(f"PDF generation reported {result.err} error(s)")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    build()
