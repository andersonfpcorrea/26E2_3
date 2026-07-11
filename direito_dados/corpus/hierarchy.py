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
