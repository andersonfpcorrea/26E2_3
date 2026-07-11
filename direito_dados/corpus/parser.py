"""Split a norm's plain text into article-level units with vigência metadata."""

import re

from direito_dados.corpus.annotations import extract_annotations, status_from_annotations
from direito_dados.corpus.models import Article, HierarchyLevel, Norm

# Article header: "Art. 155.", "Art. 155 -", "Art. 121-A." (optional letter suffix).
# Also tolerates an ordinal marker ("º" or the letter "o") that trails the
# number on its own line, e.g. "Art. 1\nº - Não há crime..." (real Planalto
# line breaks), so the marker itself is consumed and never becomes the caput.
_ARTICLE_HEADER_RE = re.compile(
    r"(?m)^\s*Art\.\s*(\d+(?:-[A-Z])?)\s*(?:[ºo]\s*)?[.\-–]?\s*"
)


def split_articles(norm_id: str, plain_text: str) -> list[Article]:
    matches = list(_ARTICLE_HEADER_RE.finditer(plain_text))
    articles: list[Article] = []
    for i, match in enumerate(matches):
        number = match.group(1)
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(plain_text)
        body = plain_text[body_start:body_end].strip()
        caput = body.split("\n", 1)[0].strip()
        annotations = extract_annotations(body)
        articles.append(
            Article(
                norm_id=norm_id,
                number=number,
                caput=caput,
                text=body,
                annotations=annotations,
                status=status_from_annotations(annotations),
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
