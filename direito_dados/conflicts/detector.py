"""LLM adjudication of candidate antinomias (lex specialis + semantic conflict).

Deterministic principles (superior/posterior) are computed elsewhere and passed
in as a hint; the model judges whether a real conflict is plausible and refines
the principle. Output is a CANDIDATE assessment, never a verdict.
"""

from dataclasses import dataclass

from direito_dados.generation.llm import LLMClient
from direito_dados.generation.parse import extract_json_object

CONFLICT_SYSTEM_PROMPT = (
    "Você analisa se dois dispositivos do direito penal brasileiro PODEM estar em "
    "conflito (antinomia). Nunca afirme um veredito definitivo — trata-se de um "
    "candidato para revisão humana. Considere a dica de resolução fornecida. "
    "Responda ESTRITAMENTE em JSON com as chaves: conflict (booleano), principle "
    "(um de: lex_superior, lex_specialis, lex_posterior, undetermined), rationale "
    "(texto curto), confidence (0 a 1)."
)


# JSON schema constraining Ollama's structured output to a conflict verdict.
_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "conflict": {"type": "boolean"},
        "principle": {"type": "string"},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["conflict", "principle", "confidence"],
}


@dataclass
class ConflictVerdict:
    conflict: bool
    principle: str
    rationale: str
    confidence: float


def build_conflict_prompt(text_a: str, cite_a: str, text_b: str, cite_b: str, hint: str) -> str:
    return (
        f"DISPOSITIVO A [{cite_a}]:\n{text_a}\n\n"
        f"DISPOSITIVO B [{cite_b}]:\n{text_b}\n\n"
        f"DICA DE RESOLUÇÃO: {hint}\n\n"
        "Eles podem estar em conflito? Responda em JSON."
    )


def adjudicate(text_a: str, cite_a: str, text_b: str, cite_b: str, hint: str,
               llm: LLMClient) -> ConflictVerdict:
    raw = llm.generate(build_conflict_prompt(text_a, cite_a, text_b, cite_b, hint),
                       system=CONFLICT_SYSTEM_PROMPT, format=_VERDICT_SCHEMA)
    data = extract_json_object(raw)
    if data is None:
        return ConflictVerdict(conflict=False, principle="undetermined",
                               rationale=raw.strip(), confidence=0.0)
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return ConflictVerdict(
        conflict=bool(data.get("conflict", False)),
        principle=str(data.get("principle", "undetermined")),
        rationale=str(data.get("rationale", "")).strip(),
        confidence=confidence,
    )
