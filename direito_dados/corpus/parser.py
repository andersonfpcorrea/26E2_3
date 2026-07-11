"""Split a norm's plain text into article-level units with vigência metadata."""

import re

from direito_dados.corpus.annotations import article_status, extract_annotations
from direito_dados.corpus.models import Article, HierarchyLevel, Norm

# Article header: "Art. 155.", "Art. 155 -", "Art. 121-A." (letter suffix,
# possibly chained as in "Art. 359-M-A" for later-inserted subdivisions).
# Also tolerates an ordinal marker ("º" or the letter "o") that trails the
# number on its own line, e.g. "Art. 1\nº - Não há crime..." (real Planalto
# line breaks), so the marker itself is consumed and never becomes the caput.
_ARTICLE_HEADER_RE = re.compile(
    r"(?m)^\s*Art\.\s*(\d+(?:-[A-Z])*)\s*(?:[ºo]\s*)?[.\-–]?\s*"
)


def _extract_caput(body: str) -> str:
    """First logical line of an article body.

    Real Planalto text wraps at a fixed column, so a parenthetical
    annotation that opens on the caput's line — most importantly
    ``(Revogado ...)`` on a wholly revoked article — can have its
    closing paren pushed onto a following line, e.g. ``"(Revogado\\npela
    Lei nº 13.869, de 2019)"``. Splitting on the first ``\\n`` alone would
    truncate the caput to ``"(Revogado"``, hiding the revocation. So the
    caput is extended line by line until parentheses balance.
    """
    lines = body.split("\n")
    caput_lines = [lines[0]]
    idx = 1
    while idx < len(lines):
        joined = " ".join(caput_lines)
        if joined.count("(") <= joined.count(")"):
            break
        caput_lines.append(lines[idx])
        idx += 1
    return " ".join(caput_lines).strip()


def split_articles(norm_id: str, plain_text: str) -> list[Article]:
    matches = list(_ARTICLE_HEADER_RE.finditer(plain_text))
    articles: list[Article] = []
    for i, match in enumerate(matches):
        number = match.group(1)
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(plain_text)
        body = plain_text[body_start:body_end].strip()
        caput = _extract_caput(body)
        annotations = extract_annotations(body)
        articles.append(
            Article(
                norm_id=norm_id,
                number=number,
                caput=caput,
                text=body,
                annotations=annotations,
                status=article_status(caput, annotations),
            )
        )
    return articles


def parse_norm(
    norm_id: str, title: str, level: HierarchyLevel, plain_text: str,
    urn: str = "", domain: str = "",
) -> Norm:
    return Norm(
        id=norm_id,
        title=title,
        level=level,
        articles=split_articles(norm_id, plain_text),
        urn=urn,
        domain=domain,
    )
