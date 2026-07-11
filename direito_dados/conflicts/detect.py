"""Orchestrate antinomy detection: candidates -> deterministic hint -> LLM
adjudication -> confirmed CANDIDATE conflicts -> conflict_candidate graph edges.

Detected conflicts are never asserted as verdicts (candidate-transparency
stance): the resulting graph edges carry verification_state=CANDIDATE and a
confidence, for human review.
"""

from dataclasses import dataclass

from direito_dados.conflicts.candidates import CandidatePair
from direito_dados.conflicts.detector import adjudicate
from direito_dados.conflicts.principles import (
    ResolutionPrinciple, deterministic_principle, principle_hint,
)
from direito_dados.corpus.loader import Corpus
from direito_dados.generation.llm import LLMClient
from direito_dados.graph.models import Edge, EdgeKind, NormGraph, Provenance, VerificationState
from direito_dados.retrieval.chunks import Chunk

_EXTRACTOR = "antinomy-detector"


@dataclass(frozen=True)
class Conflict:
    a: str
    b: str
    principle: str
    rationale: str
    confidence: float


def detect_conflicts(candidates: list[CandidatePair], chunks_by_id: dict[str, Chunk],
                     corpus: Corpus, llm: LLMClient, min_confidence: float = 0.5) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for cand in candidates:
        chunk_a = chunks_by_id[cand.a]
        chunk_b = chunks_by_id[cand.b]
        level_a = corpus.norm(chunk_a.metadata["norm_id"]).level
        level_b = corpus.norm(chunk_b.metadata["norm_id"]).level
        hint = principle_hint(level_a, level_b, None, None)
        verdict = adjudicate(
            chunk_a.text, chunk_a.metadata["citation"],
            chunk_b.text, chunk_b.metadata["citation"], hint, llm,
        )
        if not verdict.conflict or verdict.confidence < min_confidence:
            continue
        if verdict.principle and verdict.principle != ResolutionPrinciple.UNDETERMINED.value:
            principle = verdict.principle
        else:
            principle = deterministic_principle(level_a, level_b, None, None).value
        conflicts.append(Conflict(
            a=cand.a, b=cand.b, principle=principle,
            rationale=verdict.rationale, confidence=verdict.confidence,
        ))
    return conflicts


def add_conflict_edges(graph: NormGraph, conflicts: list[Conflict]) -> None:
    for conflict in conflicts:
        a, b = sorted((conflict.a, conflict.b))
        graph.add_edge(Edge(
            kind=EdgeKind.CONFLICT_CANDIDATE,
            src=a,
            dst=b,
            provenance=Provenance(source=_EXTRACTOR, extracted_by=_EXTRACTOR),
            verification_state=VerificationState.CANDIDATE,
            confidence=conflict.confidence,
            attrs={"principle": conflict.principle, "rationale": conflict.rationale},
        ))
