"""Grounded, cited RAG: retrieve in-force provisions, generate, verify citations, abstain."""

from dataclasses import dataclass, field

from direito_dados.generation.llm import LLMClient
from direito_dados.generation.parse import parse_answer
from direito_dados.generation.prompt import SYSTEM_PROMPT, build_user_prompt
from direito_dados.retrieval.embedder import Embedder
from direito_dados.retrieval.index import VectorIndex


# JSON schema that constrains Ollama's structured output to our answer shape.
_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "hierarchy_notes": {"type": "string"},
        "abstained": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": ["answer", "citations", "abstained", "confidence"],
}


@dataclass
class RagAnswer:
    answer: str
    citations: list[str] = field(default_factory=list)
    hallucinated_citations: list[str] = field(default_factory=list)
    hierarchy_notes: str = ""
    abstained: bool = False
    confidence: float = 0.0
    retrieved_ids: list[str] = field(default_factory=list)


def answer_question(question: str, index: VectorIndex, embedder: Embedder,
                    llm: LLMClient, k: int = 5, valid_ids: set[str] | None = None) -> RagAnswer:
    """Answer a question grounded in retrieved, in-force provisions.

    Retrieves the top-k in-force chunks (`exclude_revoked=True`); if none are
    found, abstains WITHOUT calling the model. Otherwise builds the cited-context
    prompt, generates, parses the structured JSON answer, and verifies every
    cited id against the retrieved set (plus `valid_ids`, if given, for a
    broader corpus-existence check) — ids that don't verify are reported as
    `hallucinated_citations` and excluded from `citations`.
    """
    results = index.query(question, embedder, k=k, exclude_revoked=True)
    retrieved_ids = [r.id for r in results]
    if not results:
        return RagAnswer(answer="Não há base suficiente nas normas para responder.",
                         abstained=True, retrieved_ids=[])

    prompt = build_user_prompt(question, results)
    raw = llm.generate(prompt, system=SYSTEM_PROMPT, format=_ANSWER_SCHEMA)
    parsed = parse_answer(raw)

    allowed = set(retrieved_ids)
    if valid_ids is not None:
        allowed = allowed | valid_ids
    verified = [c for c in parsed.citations if c in allowed]
    hallucinated = [c for c in parsed.citations if c not in allowed]

    return RagAnswer(
        answer=parsed.answer,
        citations=verified,
        hallucinated_citations=hallucinated,
        hierarchy_notes=parsed.hierarchy_notes,
        abstained=parsed.abstained,
        confidence=parsed.confidence,
        retrieved_ids=retrieved_ids,
    )
