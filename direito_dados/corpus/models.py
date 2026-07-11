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
    urn: str = ""
    domain: str = ""

    def article(self, number: str) -> Article | None:
        for art in self.articles:
            if art.number == number:
                return art
        return None
