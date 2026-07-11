"""PlanaltoAdapter — ingests Planalto consolidated texts (the graded source)."""

from direito_dados.corpus.hierarchy import level_for_norm_type
from direito_dados.corpus.models import Norm
from direito_dados.corpus.parser import parse_norm
from direito_dados.corpus.registry import NormSpec


class PlanaltoAdapter:
    """SourceAdapter over Planalto consolidated texts."""

    source_name = "planalto"

    def fetch(self, spec: NormSpec, raw_dir: str) -> str:
        # Network path; reuses corpus.fetch. Imported lazily to keep the tested path offline.
        from direito_dados.corpus.fetch import download_norm

        return download_norm(spec, raw_dir)

    def parse(self, raw_text: str, spec: NormSpec) -> Norm:
        return parse_norm(
            spec.id, spec.title, level_for_norm_type(spec.norm_type), raw_text,
            urn=spec.urn, domain=spec.domain,
        )
