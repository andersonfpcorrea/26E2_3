"""Load norms from local raw text into an in-memory queryable Corpus."""

from dataclasses import dataclass, field
from pathlib import Path

from direito_dados.corpus.hierarchy import level_for_norm_type
from direito_dados.corpus.models import Article, Norm, VigenciaStatus
from direito_dados.corpus.parser import parse_norm
from direito_dados.corpus.registry import NORMS, NormSpec


def load_norm(spec: NormSpec, raw_dir: str) -> Norm:
    text = Path(raw_dir, spec.filename).read_text(encoding="utf-8")
    return parse_norm(
        spec.id, spec.title, level_for_norm_type(spec.norm_type), text,
        urn=spec.urn, domain=spec.domain,
    )


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
