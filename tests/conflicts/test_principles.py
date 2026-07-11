from direito_dados.corpus.models import HierarchyLevel
from direito_dados.conflicts.principles import (
    ResolutionPrinciple, deterministic_principle, principle_hint,
)

def test_different_hierarchy_is_lex_superior():
    p = deterministic_principle(HierarchyLevel.CONSTITUICAO, HierarchyLevel.LEI_ORDINARIA, 1988, 2006)
    assert p == ResolutionPrinciple.LEX_SUPERIOR

def test_same_rank_different_year_is_lex_posterior():
    p = deterministic_principle(HierarchyLevel.LEI_ORDINARIA, HierarchyLevel.LEI_ORDINARIA, 1990, 2006)
    assert p == ResolutionPrinciple.LEX_POSTERIOR

def test_same_rank_same_or_unknown_year_is_undetermined():
    assert deterministic_principle(HierarchyLevel.LEI_ORDINARIA, HierarchyLevel.LEI_ORDINARIA, 2006, 2006) == ResolutionPrinciple.UNDETERMINED
    assert deterministic_principle(HierarchyLevel.LEI_ORDINARIA, HierarchyLevel.LEI_ORDINARIA, None, 2006) == ResolutionPrinciple.UNDETERMINED

def test_hint_is_nonempty_portuguese():
    h = principle_hint(HierarchyLevel.CONSTITUICAO, HierarchyLevel.LEI_ORDINARIA, 1988, 2006)
    assert "lex superior" in h.lower()
