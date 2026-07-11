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
