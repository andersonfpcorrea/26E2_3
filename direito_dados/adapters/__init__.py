"""Public API for source adapters."""

from direito_dados.adapters.base import SourceAdapter
from direito_dados.adapters.planalto import PlanaltoAdapter

__all__ = ["PlanaltoAdapter", "SourceAdapter"]
