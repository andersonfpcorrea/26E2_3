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
