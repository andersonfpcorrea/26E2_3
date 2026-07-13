"""Grounded, cited RAG: retrieve in-force provisions, generate, verify citations, abstain."""

import re
from dataclasses import dataclass, field

from direito_dados.generation.llm import LLMClient
from direito_dados.generation.parse import extract_json_object, parse_answer
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

# Quote-then-answer variant: `trecho_citado` comes FIRST so the (autoregressive)
# model commits to the literal supporting excerpt before writing the answer.
_ANSWER_SCHEMA_QUOTED = {
    "type": "object",
    "properties": {
        "trecho_citado": {"type": "string"},
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "hierarchy_notes": {"type": "string"},
        "abstained": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": ["trecho_citado", "answer", "citations", "abstained", "confidence"],
}

_QUOTE_INSTRUCTION = (
    '\n\nAntes de redigir "answer", preencha "trecho_citado" com uma FRASE COPIADA '
    "LITERALMENTE do texto do dispositivo que sustenta a resposta — palavra por "
    "palavra, sem parafrasear. NÃO é o id do dispositivo; é o texto dele. "
    'Exemplo: se a resposta se apoia no art. 121, "trecho_citado" seria algo como '
    '"Matar alguém: Pena - reclusão, de seis a vinte anos".'
    "\n\nATENÇÃO — perguntas agregadas: se a pergunta exigir comparar ou varrer TODAS "
    "as normas (ex.: qual a maior/menor pena, quantos crimes existem, qual lei tem "
    "mais artigos), ela NÃO pode ser respondida a partir de alguns trechos "
    'recuperados. Nesse caso defina "abstained": true e explique em "answer" que a '
    "pergunta é analítica e exigiria varrer o corpus inteiro, não a recuperação de "
    "trechos semelhantes."
)

_AGGREGATE_RE = re.compile(
    r"(?i)quant[oa]s\b"
    r"|\btodas?\s+as\s+(leis|normas)\b"
    r"|\bqual\s+(a\s+)?(lei|norma)\s+(tem|possui|com)\b"
    r"|\b(maior|menor|mais\s+(alta|baixa|severa|dura|grave|pesada|branda|leve|suave))\b.{0,30}\bpena\b"
    r"|\bpena\s+(máxima|mínima|maior|menor|mais\s+(alta|baixa|severa|dura|grave|pesada|branda|leve|suave))\b"
    r"|\bmais\s+(alterad|emendad|modificad)"
)

_AGGREGATE_ANSWER = (
    "Esta é uma pergunta analítica: responder exigiria varrer e comparar TODAS as "
    "normas do corpus, o que a recuperação de trechos semelhantes não faz — e uma "
    "resposta baseada em alguns trechos seria enganosa. Use as abas analíticas "
    "('A lei no tempo', 'Vigência') para agregações, ou reformule para uma "
    "pergunta sobre um dispositivo/tema específico (ex.: 'qual a pena para X?')."
)


def is_aggregate_question(question: str) -> bool:
    """Aggregation/superlative questions (max/count/compare-all) cannot be
    answered by top-k retrieval; they need the structured analytics layer."""
    return bool(_AGGREGATE_RE.search(question))


# quote_status values (see _verify_quote).
QUOTE_VERIFIED = "verificado"
QUOTE_MISATTRIBUTED = "atribuicao_incorreta"
QUOTE_NOT_FOUND = "nao_encontrado"


@dataclass
class RagAnswer:
    answer: str
    citations: list[str] = field(default_factory=list)
    hallucinated_citations: list[str] = field(default_factory=list)
    hierarchy_notes: str = ""
    abstained: bool = False
    confidence: float = 0.0
    retrieved_ids: list[str] = field(default_factory=list)
    # Quote-then-answer fields (populated only when verify_quote=True).
    quote: str = ""
    quote_status: str = ""
    quote_found_in: str = ""


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _verify_quote(quote: str, cited: list[str], results) -> tuple[str, str]:
    """Check the model's literal excerpt against the retrieved provision texts.

    Returns (status, found_in_id):
    - QUOTE_VERIFIED: the excerpt exists inside a provision the answer cites;
    - QUOTE_MISATTRIBUTED: the excerpt exists in a *different* retrieved
      provision than the one(s) cited — the content/citation mismatch that id
      verification alone cannot catch;
    - QUOTE_NOT_FOUND: the excerpt does not appear in any retrieved provision.
    """
    needle = _normalize(quote)
    # A too-short excerpt (an id, a single word like a rubrica) verifies
    # vacuously and grounds nothing — treat it as not found.
    if len(needle) < 10:
        return QUOTE_NOT_FOUND, ""
    texts = {r.id: _normalize(r.text) for r in results}
    for cid in cited:
        if cid in texts and needle in texts[cid]:
            return QUOTE_VERIFIED, cid
    for rid, text in texts.items():
        if needle in text:
            return QUOTE_MISATTRIBUTED, rid
    return QUOTE_NOT_FOUND, ""


def answer_question(question: str, index: VectorIndex, embedder: Embedder,
                    llm: LLMClient, k: int = 5, valid_ids: set[str] | None = None,
                    verify_quote: bool = False) -> RagAnswer:
    """Answer a question grounded in retrieved, in-force provisions.

    Retrieves the top-k in-force chunks (`exclude_revoked=True`); if none are
    found, abstains WITHOUT calling the model. Otherwise builds the cited-context
    prompt, generates, parses the structured JSON answer, and verifies every
    cited id against the retrieved set (plus `valid_ids`, if given, for a
    broader corpus-existence check) — ids that don't verify are reported as
    `hallucinated_citations` and excluded from `citations`.

    With `verify_quote=True` (quote-then-answer), the model must also copy the
    literal excerpt that supports the answer into `trecho_citado`, generated
    BEFORE the answer, and the excerpt is checked programmatically against the
    retrieved texts — upgrading the guarantee from "the cited id exists" to
    "the supporting content is anchored in the cited provision".
    """
    if verify_quote and is_aggregate_question(question):
        return RagAnswer(answer=_AGGREGATE_ANSWER, abstained=True, retrieved_ids=[])

    results = index.query(question, embedder, k=k, exclude_revoked=True)
    retrieved_ids = [r.id for r in results]
    if not results:
        return RagAnswer(answer="Não há base suficiente nas normas para responder.",
                         abstained=True, retrieved_ids=[])

    prompt = build_user_prompt(question, results)
    system = SYSTEM_PROMPT + _QUOTE_INSTRUCTION if verify_quote else SYSTEM_PROMPT
    schema = _ANSWER_SCHEMA_QUOTED if verify_quote else _ANSWER_SCHEMA
    raw = llm.generate(prompt, system=system, format=schema)
    parsed = parse_answer(raw)

    allowed = set(retrieved_ids)
    if valid_ids is not None:
        allowed = allowed | valid_ids
    verified = [c for c in parsed.citations if c in allowed]
    hallucinated = [c for c in parsed.citations if c not in allowed]

    answer = RagAnswer(
        answer=parsed.answer,
        citations=verified,
        hallucinated_citations=hallucinated,
        hierarchy_notes=parsed.hierarchy_notes,
        abstained=parsed.abstained,
        confidence=parsed.confidence,
        retrieved_ids=retrieved_ids,
    )
    if verify_quote and not answer.abstained:
        data = extract_json_object(raw) or {}
        answer.quote = str(data.get("trecho_citado", "")).strip()
        answer.quote_status, answer.quote_found_in = _verify_quote(
            answer.quote, verified, results)
    return answer
