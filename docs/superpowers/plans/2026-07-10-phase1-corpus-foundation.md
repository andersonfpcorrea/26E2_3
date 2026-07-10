# Phase 1 — Corpus Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `corpus` module — the single source of truth that parses Brazilian criminal-law texts into article-level units with vigência (validity) and hierarchy metadata, queryable in memory.

**Architecture:** A small Python package `direito_dados` with a `corpus` subpackage. Pure-Python parsing of already-downloaded Planalto consolidated texts (no network in the tested path). Deep module: downstream code (retrieval, conflicts, analytics) depends only on the public `corpus` API — `Norm`, `Article`, `VigenciaStatus`, `HierarchyLevel`, and a `Corpus` container — never on raw text.

**Tech Stack:** Python 3.11+, pytest, dataclasses + enums, `re` (stdlib) for annotation parsing, `beautifulsoup4` + `lxml` for HTML extraction. Fetching (network) uses `requests` but is isolated from tested logic.

## Global Constraints

- Python 3.11+ (uses `X | None` union syntax and `match` where useful).
- All code in package `direito_dados/`; tests in `tests/` mirroring the package path.
- No secrets, API keys, or tokens anywhere in the repo (rubric requirement).
- Corpus is federal criminal-law only (9 norms): CF, CP, CPP, LEP, Lei de Drogas (11.343), Maria da Penha (11.340), Crimes Hediondos (8.072), Contravenções Penais (DL 3.688), LINDB.
- Vigência is derived from Planalto inline annotations; `tácita`/inconstitucionalidade cases are NOT decided here (surfaced later as candidates).
- Each task ends with a passing test and a commit. TDD: test first, watch it fail, implement minimally, watch it pass, commit.

---

### Task 1: Project scaffold + data models

**Files:**
- Create: `pyproject.toml`
- Create: `direito_dados/__init__.py`
- Create: `direito_dados/corpus/__init__.py`
- Create: `direito_dados/corpus/models.py`
- Create: `tests/__init__.py`
- Create: `tests/corpus/__init__.py`
- Create: `tests/corpus/test_models.py`
- Create: `.gitignore` (append)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `HierarchyLevel(Enum)` with members `CONSTITUICAO=1`, `LEI_COMPLEMENTAR=2`, `LEI_ORDINARIA=3`, `DECRETO_LEI=3`, `MEDIDA_PROVISORIA=3`, `DECRETO=4`, `INFRALEGAL=5` (value = rank; lower rank wins under lex superior).
  - `VigenciaStatus(Enum)`: `VIGENTE="vigente"`, `ALTERADO="alterado"`, `REVOGADO="revogado"`.
  - `Annotation(kind: str, law_ref: str, year: int | None)` — frozen dataclass.
  - `Article(norm_id: str, number: str, caput: str, text: str, annotations: list[Annotation], status: VigenciaStatus)`; property `citation -> str` returns `"{norm_id} art. {number}"`.
  - `Norm(id: str, title: str, level: HierarchyLevel, articles: list[Article])`; method `article(number: str) -> Article | None`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "direito-dados"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init files**

Create empty files: `direito_dados/__init__.py`, `direito_dados/corpus/__init__.py`, `tests/__init__.py`, `tests/corpus/__init__.py`.

- [ ] **Step 3: Append to `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
.env
data/raw/*.html
```

- [ ] **Step 4: Write the failing test** — `tests/corpus/test_models.py`

```python
from direito_dados.corpus.models import (
    Annotation,
    Article,
    HierarchyLevel,
    Norm,
    VigenciaStatus,
)


def test_article_citation_is_norm_and_number():
    art = Article(norm_id="CP", number="155", caput="Subtrair...", text="Subtrair...")
    assert art.citation == "CP art. 155"


def test_article_defaults_to_vigente_with_no_annotations():
    art = Article(norm_id="CP", number="121", caput="Matar alguém", text="Matar alguém")
    assert art.status == VigenciaStatus.VIGENTE
    assert art.annotations == []


def test_norm_lookup_by_article_number():
    art = Article(norm_id="CP", number="155", caput="c", text="t")
    norm = Norm(id="CP", title="Código Penal", level=HierarchyLevel.DECRETO_LEI, articles=[art])
    assert norm.article("155") is art
    assert norm.article("999") is None


def test_hierarchy_constituicao_outranks_lei():
    assert HierarchyLevel.CONSTITUICAO.value < HierarchyLevel.LEI_ORDINARIA.value


def test_annotation_is_hashable_frozen():
    a = Annotation(kind="revogado", law_ref="Lei nº 11.106", year=2005)
    assert a.year == 2005
    assert {a, a} == {a}
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python -m pytest tests/corpus/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.models'`.

- [ ] **Step 6: Write minimal implementation** — `direito_dados/corpus/models.py`

```python
"""Core data models for the Brazilian criminal-law corpus."""

from dataclasses import dataclass, field
from enum import Enum


class HierarchyLevel(Enum):
    """Position in the norm hierarchy. Lower value = higher rank (lex superior)."""

    CONSTITUICAO = 1
    LEI_COMPLEMENTAR = 2
    LEI_ORDINARIA = 3
    DECRETO_LEI = 3
    MEDIDA_PROVISORIA = 3
    DECRETO = 4
    INFRALEGAL = 5


class VigenciaStatus(Enum):
    VIGENTE = "vigente"
    ALTERADO = "alterado"
    REVOGADO = "revogado"


@dataclass(frozen=True)
class Annotation:
    """A Planalto inline annotation on a provision (amendment, revocation, etc.)."""

    kind: str
    law_ref: str
    year: int | None


@dataclass
class Article:
    norm_id: str
    number: str
    caput: str
    text: str
    annotations: list[Annotation] = field(default_factory=list)
    status: VigenciaStatus = VigenciaStatus.VIGENTE

    @property
    def citation(self) -> str:
        return f"{self.norm_id} art. {self.number}"


@dataclass
class Norm:
    id: str
    title: str
    level: HierarchyLevel
    articles: list[Article] = field(default_factory=list)

    def article(self, number: str) -> Article | None:
        for art in self.articles:
            if art.number == number:
                return art
        return None
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/corpus/test_models.py -v`
Expected: PASS (5 passed).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore direito_dados tests
git commit -m "feat(corpus): project scaffold and core data models"
```

---

### Task 2: Hierarchy classification + lex-superior comparator

**Files:**
- Create: `direito_dados/corpus/hierarchy.py`
- Create: `tests/corpus/test_hierarchy.py`

**Interfaces:**
- Consumes: `HierarchyLevel` from Task 1.
- Produces:
  - `level_for_norm_type(norm_type: str) -> HierarchyLevel` — maps a norm-type string (`"constituicao"`, `"lei_ordinaria"`, `"lei_complementar"`, `"decreto_lei"`, `"medida_provisoria"`, `"decreto"`) to a `HierarchyLevel`; raises `ValueError` on unknown type.
  - `prevails_by_hierarchy(a: HierarchyLevel, b: HierarchyLevel) -> HierarchyLevel | None` — returns the higher-ranked level under *lex superior*, or `None` if equal rank (unresolved by hierarchy alone).

- [ ] **Step 1: Write the failing test** — `tests/corpus/test_hierarchy.py`

```python
import pytest

from direito_dados.corpus.hierarchy import level_for_norm_type, prevails_by_hierarchy
from direito_dados.corpus.models import HierarchyLevel


def test_level_for_known_norm_types():
    assert level_for_norm_type("constituicao") == HierarchyLevel.CONSTITUICAO
    assert level_for_norm_type("lei_ordinaria") == HierarchyLevel.LEI_ORDINARIA
    assert level_for_norm_type("decreto_lei") == HierarchyLevel.DECRETO_LEI


def test_level_for_unknown_norm_type_raises():
    with pytest.raises(ValueError):
        level_for_norm_type("portaria_municipal")


def test_constituicao_prevails_over_lei():
    winner = prevails_by_hierarchy(HierarchyLevel.LEI_ORDINARIA, HierarchyLevel.CONSTITUICAO)
    assert winner == HierarchyLevel.CONSTITUICAO


def test_equal_rank_is_unresolved_by_hierarchy():
    # decreto-lei and lei ordinária share rank 3 -> hierarchy cannot decide
    assert prevails_by_hierarchy(HierarchyLevel.DECRETO_LEI, HierarchyLevel.LEI_ORDINARIA) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/corpus/test_hierarchy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.hierarchy'`.

- [ ] **Step 3: Write minimal implementation** — `direito_dados/corpus/hierarchy.py`

```python
"""Norm-hierarchy classification and lex-superior resolution.

Only *lex superior* (higher norm prevails) is decided here. *Lex specialis*
and *lex posterior* require generality and date reasoning and are handled by
the conflicts module, not by hierarchy alone.
"""

from direito_dados.corpus.models import HierarchyLevel

_NORM_TYPE_TO_LEVEL = {
    "constituicao": HierarchyLevel.CONSTITUICAO,
    "lei_complementar": HierarchyLevel.LEI_COMPLEMENTAR,
    "lei_ordinaria": HierarchyLevel.LEI_ORDINARIA,
    "decreto_lei": HierarchyLevel.DECRETO_LEI,
    "medida_provisoria": HierarchyLevel.MEDIDA_PROVISORIA,
    "decreto": HierarchyLevel.DECRETO,
}


def level_for_norm_type(norm_type: str) -> HierarchyLevel:
    try:
        return _NORM_TYPE_TO_LEVEL[norm_type]
    except KeyError as exc:
        raise ValueError(f"Unknown norm type: {norm_type!r}") from exc


def prevails_by_hierarchy(a: HierarchyLevel, b: HierarchyLevel) -> HierarchyLevel | None:
    if a.value == b.value:
        return None
    return a if a.value < b.value else b
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/corpus/test_hierarchy.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add direito_dados/corpus/hierarchy.py tests/corpus/test_hierarchy.py
git commit -m "feat(corpus): hierarchy classification and lex-superior comparator"
```

---

### Task 3: Vigência annotation parser

**Files:**
- Create: `direito_dados/corpus/annotations.py`
- Create: `tests/corpus/test_annotations.py`

**Interfaces:**
- Consumes: `Annotation`, `VigenciaStatus` from Task 1.
- Produces:
  - `extract_annotations(text: str) -> list[Annotation]` — finds all Planalto parentheticals of kinds `redacao` (Redação dada), `revogado` (Revogado), `incluido` (Incluído), `renumerado` (Renumerado), `vide` (Vide), each carrying `law_ref` like `"Lei nº 13.964"` (or `"Lei Complementar nº 7"`, or `"Decreto-Lei nº 2.848"`) and `year` when present.
  - `status_from_annotations(annotations: list[Annotation]) -> VigenciaStatus` — `REVOGADO` if any `revogado`; else `ALTERADO` if any `redacao`/`incluido`/`renumerado`; else `VIGENTE`.

- [ ] **Step 1: Write the failing test** — `tests/corpus/test_annotations.py`

```python
from direito_dados.corpus.annotations import extract_annotations, status_from_annotations
from direito_dados.corpus.models import VigenciaStatus


def test_extract_redacao_annotation():
    text = "Pena - reclusão (Redação dada pela Lei nº 13.964, de 2019)"
    anns = extract_annotations(text)
    assert len(anns) == 1
    assert anns[0].kind == "redacao"
    assert anns[0].law_ref == "Lei nº 13.964"
    assert anns[0].year == 2019


def test_extract_revogado_annotation():
    text = "Art. 240. (Revogado pela Lei nº 11.106, de 2005)"
    anns = extract_annotations(text)
    assert anns[0].kind == "revogado"
    assert anns[0].year == 2005


def test_extract_multiple_annotations():
    text = (
        "Caput (Incluído pela Lei nº 12.015, de 2009). "
        "§ 1º (Redação dada pela Lei nº 13.718, de 2018)"
    )
    anns = extract_annotations(text)
    kinds = {a.kind for a in anns}
    assert kinds == {"incluido", "redacao"}


def test_annotation_without_year_is_none():
    text = "(Vide Lei nº 8.072)"
    anns = extract_annotations(text)
    assert anns[0].kind == "vide"
    assert anns[0].year is None


def test_status_revogado_dominates():
    text = "(Redação dada pela Lei nº 1, de 2000) (Revogado pela Lei nº 2, de 2010)"
    assert status_from_annotations(extract_annotations(text)) == VigenciaStatus.REVOGADO


def test_status_alterado_when_only_redacao():
    text = "(Redação dada pela Lei nº 13.964, de 2019)"
    assert status_from_annotations(extract_annotations(text)) == VigenciaStatus.ALTERADO


def test_status_vigente_when_no_annotations():
    assert status_from_annotations([]) == VigenciaStatus.VIGENTE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/corpus/test_annotations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.annotations'`.

- [ ] **Step 3: Write minimal implementation** — `direito_dados/corpus/annotations.py`

```python
"""Parsing of Planalto inline vigência annotations.

Planalto consolidated texts annotate every changed provision with
parentheticals such as ``(Redação dada pela Lei nº 13.964, de 2019)`` or
``(Revogado pela Lei nº 11.106, de 2005)``. This module turns those into
structured ``Annotation`` objects and derives a ``VigenciaStatus``.
"""

import re

from direito_dados.corpus.models import Annotation, VigenciaStatus

_KIND_BY_KEYWORD = {
    "redação dada": "redacao",
    "redacao dada": "redacao",
    "revogado": "revogado",
    "revogada": "revogado",
    "incluído": "incluido",
    "incluido": "incluido",
    "renumerado": "renumerado",
    "vide": "vide",
}

# Matches the annotation body inside parentheses, capturing the kind keyword,
# the law reference (Lei / Lei Complementar / Decreto-Lei nº X) and optional year.
_ANNOTATION_RE = re.compile(
    r"\(\s*"
    r"(?P<kind>Reda[çc][ãa]o dada|Revogad[oa]|Inclu[íi]do|Renumerado|Vide)"
    r"[^)]*?"
    r"(?P<lawref>(?:Lei Complementar|Lei|Decreto-Lei|Emenda Constitucional)"
    r"\s+n[ºo]\s*[\d.]+)"
    r"(?:[^)]*?de\s+(?P<year>\d{4}))?"
    r"[^)]*\)",
    re.IGNORECASE,
)


def _normalize_kind(raw: str) -> str:
    key = raw.strip().lower()
    for keyword, kind in _KIND_BY_KEYWORD.items():
        if key.startswith(keyword):
            return kind
    return key


def _normalize_lawref(raw: str) -> str:
    # Collapse internal whitespace and standardize "nº".
    ref = re.sub(r"\s+", " ", raw).strip()
    return ref.replace("no ", "nº ").replace("No ", "nº ")


def extract_annotations(text: str) -> list[Annotation]:
    annotations: list[Annotation] = []
    for match in _ANNOTATION_RE.finditer(text):
        year_str = match.group("year")
        annotations.append(
            Annotation(
                kind=_normalize_kind(match.group("kind")),
                law_ref=_normalize_lawref(match.group("lawref")),
                year=int(year_str) if year_str else None,
            )
        )
    return annotations


def status_from_annotations(annotations: list[Annotation]) -> VigenciaStatus:
    kinds = {a.kind for a in annotations}
    if "revogado" in kinds:
        return VigenciaStatus.REVOGADO
    if kinds & {"redacao", "incluido", "renumerado"}:
        return VigenciaStatus.ALTERADO
    return VigenciaStatus.VIGENTE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/corpus/test_annotations.py -v`
Expected: PASS (7 passed). If the `nº`/`no` normalization test for `law_ref` fails on exact string, adjust `_normalize_lawref` until `"Lei nº 13.964"` matches — the test strings use `nº`.

- [ ] **Step 5: Commit**

```bash
git add direito_dados/corpus/annotations.py tests/corpus/test_annotations.py
git commit -m "feat(corpus): vigência annotation parser and status derivation"
```

---

### Task 4: Article splitter (plain-text parser)

**Files:**
- Create: `direito_dados/corpus/parser.py`
- Create: `tests/corpus/test_parser.py`

**Interfaces:**
- Consumes: `Article`, `Norm`, `HierarchyLevel` from Task 1; `extract_annotations`, `status_from_annotations` from Task 3.
- Produces:
  - `split_articles(norm_id: str, plain_text: str) -> list[Article]` — splits a norm's plain text on `Art. N` headers (handles `Art. 155.`, `Art. 155 -`, `Art. 121-A.`), sets `caput` to the first line/sentence, `text` to the full article block, and fills `annotations` + `status` via Task 3. Text before the first `Art.` is ignored.
  - `parse_norm(norm_id: str, title: str, level: HierarchyLevel, plain_text: str) -> Norm`.

- [ ] **Step 1: Write the failing test** — `tests/corpus/test_parser.py`

```python
from direito_dados.corpus.models import HierarchyLevel, VigenciaStatus
from direito_dados.corpus.parser import parse_norm, split_articles

SAMPLE = """PARTE ESPECIAL
TÍTULO I

Art. 121. Matar alguém:
Pena - reclusão, de seis a vinte anos.

Art. 155. Subtrair, para si ou para outrem, coisa alheia móvel:
Pena - reclusão, de um a quatro anos (Redação dada pela Lei nº 13.654, de 2018).

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""


def test_splits_on_article_headers():
    arts = split_articles("CP", SAMPLE)
    assert [a.number for a in arts] == ["121", "155", "240"]


def test_caput_is_first_line_of_article():
    arts = split_articles("CP", SAMPLE)
    assert arts[0].caput.startswith("Matar alguém")


def test_amended_article_marked_alterado():
    arts = split_articles("CP", SAMPLE)
    art155 = next(a for a in arts if a.number == "155")
    assert art155.status == VigenciaStatus.ALTERADO
    assert any(ann.year == 2018 for ann in art155.annotations)


def test_revoked_article_marked_revogado():
    arts = split_articles("CP", SAMPLE)
    art240 = next(a for a in arts if a.number == "240")
    assert art240.status == VigenciaStatus.REVOGADO


def test_text_before_first_article_ignored():
    arts = split_articles("CP", SAMPLE)
    assert all("PARTE ESPECIAL" not in a.text for a in arts)


def test_parse_norm_builds_norm_object():
    norm = parse_norm("CP", "Código Penal", HierarchyLevel.DECRETO_LEI, SAMPLE)
    assert norm.id == "CP"
    assert norm.level == HierarchyLevel.DECRETO_LEI
    assert norm.article("121") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/corpus/test_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.parser'`.

- [ ] **Step 3: Write minimal implementation** — `direito_dados/corpus/parser.py`

```python
"""Split a norm's plain text into article-level units with vigência metadata."""

import re

from direito_dados.corpus.annotations import extract_annotations, status_from_annotations
from direito_dados.corpus.models import Article, HierarchyLevel, Norm

# Article header: "Art. 155.", "Art. 155 -", "Art. 121-A." (optional letter suffix).
_ARTICLE_HEADER_RE = re.compile(r"(?m)^\s*Art\.\s*(\d+(?:-[A-Z])?)\s*[.\-–]?\s*")


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
    norm_id: str, title: str, level: HierarchyLevel, plain_text: str
) -> Norm:
    return Norm(
        id=norm_id,
        title=title,
        level=level,
        articles=split_articles(norm_id, plain_text),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/corpus/test_parser.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add direito_dados/corpus/parser.py tests/corpus/test_parser.py
git commit -m "feat(corpus): article splitter with vigência metadata"
```

---

### Task 5: Norm registry + Corpus container + public API

**Files:**
- Create: `direito_dados/corpus/registry.py`
- Create: `direito_dados/corpus/loader.py`
- Modify: `direito_dados/corpus/__init__.py`
- Create: `tests/corpus/test_registry.py`
- Create: `tests/corpus/test_loader.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `registry.NORMS: dict[str, NormSpec]` where `NormSpec(id: str, title: str, norm_type: str, source_url: str, filename: str)` — the 9 criminal-microsystem norms.
  - `loader.load_norm(spec: NormSpec, raw_dir: str) -> Norm` — reads `{raw_dir}/{spec.filename}`, parses to a `Norm` using `parse_norm` + `level_for_norm_type`.
  - `loader.Corpus` — container with `norms: list[Norm]`; methods `norm(id: str) -> Norm | None`, `all_articles() -> list[Article]`, `in_force_articles() -> list[Article]` (status != REVOGADO).
  - `loader.load_corpus(raw_dir: str, specs: list[NormSpec] | None = None) -> Corpus`.
  - Public re-exports in `corpus/__init__.py`: `Norm`, `Article`, `Annotation`, `VigenciaStatus`, `HierarchyLevel`, `Corpus`, `load_corpus`, `NORMS`.

- [ ] **Step 1: Write the failing test** — `tests/corpus/test_registry.py`

```python
from direito_dados.corpus.registry import NORMS


def test_registry_has_nine_criminal_norms():
    assert len(NORMS) == 9
    assert set(NORMS) == {
        "CF", "CP", "CPP", "LEP", "L11343", "L11340", "L8072", "DL3688", "LINDB"
    }


def test_registry_specs_have_source_and_filename():
    for spec in NORMS.values():
        assert spec.source_url.startswith("http")
        assert spec.filename.endswith(".txt")
        assert spec.norm_type
```

- [ ] **Step 2: Run registry test to verify it fails**

Run: `python -m pytest tests/corpus/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.registry'`.

- [ ] **Step 3: Write `registry.py`**

```python
"""Static registry of the federal criminal-law microsystem (9 norms)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NormSpec:
    id: str
    title: str
    norm_type: str
    source_url: str
    filename: str


def _spec(id_, title, norm_type, url):
    return NormSpec(id=id_, title=title, norm_type=norm_type, source_url=url,
                    filename=f"{id_}.txt")


NORMS: dict[str, NormSpec] = {
    s.id: s
    for s in [
        _spec("CF", "Constituição Federal de 1988", "constituicao",
              "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"),
        _spec("CP", "Código Penal (DL 2.848/1940)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"),
        _spec("CPP", "Código de Processo Penal (DL 3.689/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm"),
        _spec("LEP", "Lei de Execução Penal (7.210/1984)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l7210compilado.htm"),
        _spec("L11343", "Lei de Drogas (11.343/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11343.htm"),
        _spec("L11340", "Lei Maria da Penha (11.340/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm"),
        _spec("L8072", "Crimes Hediondos (8.072/1990)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm"),
        _spec("DL3688", "Contravenções Penais (DL 3.688/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm"),
        _spec("LINDB", "LINDB (DL 4.657/1942)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm"),
    ]
}
```

- [ ] **Step 4: Run registry test to verify it passes**

Run: `python -m pytest tests/corpus/test_registry.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Write the failing loader test** — `tests/corpus/test_loader.py`

```python
from direito_dados.corpus.loader import Corpus, load_corpus
from direito_dados.corpus.registry import NormSpec
from direito_dados.corpus.models import VigenciaStatus

FIXTURE = """Art. 1. Norma vigente qualquer.

Art. 2. (Revogado pela Lei nº 99, de 2001)
"""


def test_load_norm_and_corpus_from_raw_dir(tmp_path):
    (tmp_path / "TST.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="TST", title="Teste", norm_type="lei_ordinaria",
                    source_url="http://x", filename="TST.txt")
    corpus = load_corpus(str(tmp_path), specs=[spec])
    assert isinstance(corpus, Corpus)
    assert corpus.norm("TST") is not None
    assert len(corpus.all_articles()) == 2


def test_in_force_articles_excludes_revogado(tmp_path):
    (tmp_path / "TST.txt").write_text(FIXTURE, encoding="utf-8")
    spec = NormSpec(id="TST", title="Teste", norm_type="lei_ordinaria",
                    source_url="http://x", filename="TST.txt")
    corpus = load_corpus(str(tmp_path), specs=[spec])
    in_force = corpus.in_force_articles()
    assert [a.number for a in in_force] == ["1"]
    assert all(a.status != VigenciaStatus.REVOGADO for a in in_force)
```

- [ ] **Step 6: Run loader test to verify it fails**

Run: `python -m pytest tests/corpus/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.loader'`.

- [ ] **Step 7: Write `loader.py`**

```python
"""Load norms from local raw text into an in-memory queryable Corpus."""

from dataclasses import dataclass, field
from pathlib import Path

from direito_dados.corpus.hierarchy import level_for_norm_type
from direito_dados.corpus.models import Article, Norm, VigenciaStatus
from direito_dados.corpus.parser import parse_norm
from direito_dados.corpus.registry import NORMS, NormSpec


def load_norm(spec: NormSpec, raw_dir: str) -> Norm:
    text = Path(raw_dir, spec.filename).read_text(encoding="utf-8")
    return parse_norm(spec.id, spec.title, level_for_norm_type(spec.norm_type), text)


@dataclass
class Corpus:
    norms: list[Norm] = field(default_factory=list)

    def norm(self, id: str) -> Norm | None:
        for n in self.norms:
            if n.id == id:
                return n
        return None

    def all_articles(self) -> list[Article]:
        return [art for n in self.norms for art in n.articles]

    def in_force_articles(self) -> list[Article]:
        return [a for a in self.all_articles() if a.status != VigenciaStatus.REVOGADO]


def load_corpus(raw_dir: str, specs: list[NormSpec] | None = None) -> Corpus:
    chosen = specs if specs is not None else list(NORMS.values())
    return Corpus(norms=[load_norm(spec, raw_dir) for spec in chosen])
```

- [ ] **Step 8: Run loader test to verify it passes**

Run: `python -m pytest tests/corpus/test_loader.py -v`
Expected: PASS (2 passed).

- [ ] **Step 9: Wire the public API** — replace `direito_dados/corpus/__init__.py`

```python
"""Public API for the criminal-law corpus module."""

from direito_dados.corpus.loader import Corpus, load_corpus, load_norm
from direito_dados.corpus.models import (
    Annotation,
    Article,
    HierarchyLevel,
    Norm,
    VigenciaStatus,
)
from direito_dados.corpus.registry import NORMS, NormSpec

__all__ = [
    "Annotation",
    "Article",
    "Corpus",
    "HierarchyLevel",
    "NORMS",
    "Norm",
    "NormSpec",
    "VigenciaStatus",
    "load_corpus",
    "load_norm",
]
```

- [ ] **Step 10: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all tasks green — 26 tests total).

- [ ] **Step 11: Commit**

```bash
git add direito_dados/corpus tests/corpus
git commit -m "feat(corpus): norm registry, Corpus container, public API"
```

---

### Task 6: Fetch script for real Planalto texts (network, untested path)

**Files:**
- Create: `direito_dados/corpus/fetch.py`
- Create: `scripts/fetch_corpus.py`
- Create: `data/raw/.gitkeep`

**Interfaces:**
- Consumes: `NORMS`, `NormSpec` from Task 5; `beautifulsoup4`.
- Produces:
  - `fetch.html_to_plain_text(html: str) -> str` — strips scripts/styles, preserves article text and parentheticals, collapses whitespace. (This one IS unit-tested.)
  - `fetch.download_norm(spec: NormSpec, raw_dir: str) -> str` — GET `spec.source_url`, convert to plain text, write `{raw_dir}/{spec.filename}`, return the path. (Network; not unit-tested.)
  - `scripts/fetch_corpus.py` — CLI that downloads all 9 norms into `data/raw/`.

- [ ] **Step 1: Write the failing test** — add to `tests/corpus/test_parser.py`

```python
def test_html_to_plain_text_keeps_articles_and_annotations():
    from direito_dados.corpus.fetch import html_to_plain_text

    html = (
        "<html><head><style>x{}</style></head><body>"
        "<p>Art. 155. Subtrair coisa alheia "
        "(Redação dada pela Lei nº 13.654, de 2018).</p>"
        "<script>ignore()</script></body></html>"
    )
    text = html_to_plain_text(html)
    assert "Art. 155." in text
    assert "Lei nº 13.654" in text
    assert "ignore()" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/corpus/test_parser.py::test_html_to_plain_text_keeps_articles_and_annotations -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'direito_dados.corpus.fetch'`.

- [ ] **Step 3: Write `fetch.py`**

```python
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
    response.encoding = response.apparent_encoding or "latin-1"
    plain = html_to_plain_text(response.text)
    out_path = Path(raw_dir, spec.filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(plain, encoding="utf-8")
    return str(out_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/corpus/test_parser.py::test_html_to_plain_text_keeps_articles_and_annotations -v`
Expected: PASS.

- [ ] **Step 5: Write `scripts/fetch_corpus.py`**

```python
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
```

- [ ] **Step 6: Create `data/raw/.gitkeep`** (empty file so the dir exists; raw HTML is gitignored).

- [ ] **Step 7: Run the fetch script against the real sites** (manual, network required)

Run: `python scripts/fetch_corpus.py`
Expected: 9 lines printed, 9 `.txt` files in `data/raw/`. Spot-check one: `python -c "from direito_dados.corpus import load_corpus; c=load_corpus('data/raw'); print(len(c.all_articles()), len(c.in_force_articles()))"` — expect a few thousand articles total, in-force < total.

- [ ] **Step 8: Commit** (code only; raw `.txt` optionally committed if small enough to aid reproducibility)

```bash
git add direito_dados/corpus/fetch.py scripts/fetch_corpus.py data/raw/.gitkeep tests/corpus/test_parser.py
git commit -m "feat(corpus): Planalto fetch script and HTML-to-text reducer"
```

---

## Self-Review

**Spec coverage (Phase 1 slice only):** This plan covers Section 4.1 step 1 (ingestion), Section 3.1 (the 9-norm corpus registry), and Section 3.3 (vigência from annotations). Retrieval/indexing (4.1 steps 2–3), generation, conflicts, analytics, and evaluation are intentionally deferred to Plans 2–3. The `corpus` public API (`Corpus`, `in_force_articles`) is the interface those later plans consume.

**Placeholder scan:** No TBD/TODO. Every code step shows complete code. Task 6's network steps (`download_norm`, the fetch run) are explicitly marked untested-path with a manual verification step — that's a real boundary, not a placeholder.

**Type consistency:** `VigenciaStatus`, `HierarchyLevel`, `Article.status`, `Annotation(kind, law_ref, year)`, `Norm.article()`, `Corpus.in_force_articles()` are used identically across Tasks 1–6. `NormSpec` fields (`id, title, norm_type, source_url, filename`) match between registry, loader, and fetch.

**Known risk to validate during execution:** real Planalto HTML is messier than the fixtures (nested tables, `<font>` tags, non-breaking spaces, `art.` casing). The `split_articles` regex and `html_to_plain_text` will likely need tuning against real `data/raw` output in Task 6 — budget time for a fixture captured from one real norm and 2–3 regex adjustments. This is expected and is why the fetch/real-data task comes last, after the logic is proven on clean fixtures.
