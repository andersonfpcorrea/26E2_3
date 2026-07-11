"""Deterministic LINDB antinomy-resolution principles (the non-semantic ones).

lex superior (hierarchy) and lex posterior (date) are computable from metadata.
lex specialis (specificity) requires reading the provisions, so it is left to the
LLM adjudicator — this module only supplies a hint.
"""

from enum import Enum

from direito_dados.corpus.hierarchy import prevails_by_hierarchy
from direito_dados.corpus.models import HierarchyLevel


class ResolutionPrinciple(Enum):
    LEX_SUPERIOR = "lex_superior"
    LEX_SPECIALIS = "lex_specialis"
    LEX_POSTERIOR = "lex_posterior"
    UNDETERMINED = "undetermined"


def deterministic_principle(level_a: HierarchyLevel, level_b: HierarchyLevel,
                            year_a: int | None, year_b: int | None) -> ResolutionPrinciple:
    if prevails_by_hierarchy(level_a, level_b) is not None:
        return ResolutionPrinciple.LEX_SUPERIOR
    if year_a is not None and year_b is not None and year_a != year_b:
        return ResolutionPrinciple.LEX_POSTERIOR
    return ResolutionPrinciple.UNDETERMINED


def principle_hint(level_a: HierarchyLevel, level_b: HierarchyLevel,
                   year_a: int | None, year_b: int | None) -> str:
    p = deterministic_principle(level_a, level_b, year_a, year_b)
    if p is ResolutionPrinciple.LEX_SUPERIOR:
        return "Hierarquia distinta: lex superior pode prevalecer (norma superior derroga inferior)."
    if p is ResolutionPrinciple.LEX_POSTERIOR:
        return "Mesma hierarquia, datas distintas: lex posterior pode prevalecer (norma posterior derroga anterior)."
    return "Mesma hierarquia e data: avaliar lex specialis (a norma mais específica pode prevalecer)."
