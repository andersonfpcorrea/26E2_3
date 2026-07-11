"""The SourceAdapter interface — the seam that makes 'plug in any law' true.

A SourceAdapter knows how to fetch a norm's raw document from some source and
parse it into a Norm (article-level, with vigência). Adding a source (LexML,
Câmara/Senado, a foreign legal system) means writing a new adapter; nothing
downstream changes. The graded build ships one adapter: PlanaltoAdapter.
"""

from typing import Protocol, runtime_checkable

from direito_dados.corpus.models import Norm
from direito_dados.corpus.registry import NormSpec


@runtime_checkable
class SourceAdapter(Protocol):
    def fetch(self, spec: NormSpec, raw_dir: str) -> str:
        """Obtain the raw document for `spec`; return the local path to it."""
        ...

    def parse(self, raw_text: str, spec: NormSpec) -> Norm:
        """Parse a raw document into a Norm."""
        ...
