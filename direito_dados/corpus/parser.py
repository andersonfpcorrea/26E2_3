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


_RUBRICA_STOPWORDS_RE = re.compile(
    r"(?i)^(pena\b|§|parágrafo\b|art\.?|inciso\b|[ivxlcdm]+\s*[-–])"
)


def _is_annotationish(line: str) -> bool:
    """Line that is (part of) a Planalto parenthetical annotation."""
    s = line.strip()
    return bool(s) and (s.startswith("(") or s.endswith(")"))


def _is_rubrica_line(line: str) -> bool:
    """Heuristic for an official article heading (nomen juris).

    Rubricas are short title-case lines with no terminal punctuation, e.g.
    "Homicídio simples" or "Violação sexual mediante fraude". Structural
    headings (PARTE/TÍTULO/CAPÍTULO, all-caps section names), penalty lines,
    paragraph markers and wrapped sentence fragments are excluded.
    """
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if s[-1] in ".:;,)-–—":
        return False
    if _is_annotationish(s):
        return False
    if s.isupper():  # PARTE / TÍTULO / CAPÍTULO / "DOS CRIMES..." headings
        return False
    if not s[0].isalpha() or not s[0].isupper():
        return False
    if not any(c.islower() for c in s):
        return False
    if _RUBRICA_STOPWORDS_RE.match(s):
        return False
    return True


def _split_trailing_rubrica(body: str) -> tuple[str, str]:
    """Split a block into (remaining body, rubrica belonging to the NEXT article).

    Planalto prints each article's heading immediately before its ``Art. N``
    line, so a plain header split attaches every heading to the *previous*
    article's tail. Trailing annotation lines (which may refer to the rubrica)
    are left in place; only the contiguous heading lines are moved.
    """
    lines = body.rstrip().splitlines()
    i = len(lines)
    while i > 0 and _is_annotationish(lines[i - 1]) and (len(lines) - i) < 4:
        i -= 1
    j = i
    while j > 0 and _is_rubrica_line(lines[j - 1]) and (i - j) < 3:
        j -= 1
    if j == i:  # no rubrica found
        return body, ""
    rubrica = " ".join(line.strip() for line in lines[j:i])
    remaining = "\n".join(lines[:j] + lines[i:]).strip()
    return remaining, rubrica


def _phantom_headers(numbers: list[int]) -> set[int]:
    """Indices of headers that belong to QUOTED foreign articles, not the norm.

    Amending laws quote the articles they rewrite (e.g. Lei 8.072 art. 6º quotes
    CP arts. 213/214/223/267/270 verbatim). Those quoted headers appear as a
    block whose numbering jumps far above the norm's own sequence and whose end
    is marked by the norm's own numbering resuming. Detection: a jump of more
    than 100 above the last accepted number, with the native sequence resuming
    (a number within +20 of the last accepted) within the next few headers —
    quoted blocks are short, and the bounded window keeps genuinely long norms
    (e.g. the CPP) from being poisoned by low-numbered trailing annexes.
    """
    phantoms: set[int] = set()
    last_accepted = 0
    window = 30
    for i, num in enumerate(numbers):
        upcoming = numbers[i + 1 : i + 1 + window]
        if num > last_accepted + 100 and any(n <= last_accepted + 20 for n in upcoming):
            phantoms.add(i)
            continue
        last_accepted = num
    return phantoms


def split_articles(norm_id: str, plain_text: str) -> list[Article]:
    matches = list(_ARTICLE_HEADER_RE.finditer(plain_text))
    numbers = [int(m.group(1).split("-")[0]) for m in matches]
    phantoms = _phantom_headers(numbers)
    articles: list[Article] = []
    preamble = plain_text[: matches[0].start()] if matches else ""
    _, next_rubrica = _split_trailing_rubrica(preamble)
    for i, match in enumerate(matches):
        number = match.group(1)
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(plain_text)
        body = plain_text[body_start:body_end].strip()
        rubrica = next_rubrica
        body, next_rubrica = _split_trailing_rubrica(body)
        if i in phantoms:
            continue
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
                rubrica=rubrica,
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
