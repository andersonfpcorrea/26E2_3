"""Parse and validate the LLM's structured JSON answer, failing safe to abstention."""

import json
from dataclasses import dataclass, field


@dataclass
class ParsedAnswer:
    answer: str
    citations: list[str] = field(default_factory=list)
    hierarchy_notes: str = ""
    abstained: bool = False
    confidence: float = 0.0
    parse_ok: bool = False


def _extract_json(raw: str) -> dict | None:
    depth = 0
    start = -1
    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(raw[start:i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


def _norm_citation(c: str) -> str:
    return str(c).strip().strip("[]").strip()


def parse_answer(raw: str) -> ParsedAnswer:
    """Extract the answer's JSON payload, tolerating ```json fences and prose.

    On unparseable output, fails safe: returns an abstained ParsedAnswer with
    parse_ok=False rather than raising or fabricating a structured answer.
    """
    data = _extract_json(raw)
    if data is None:
        return ParsedAnswer(answer=raw.strip(), abstained=True, parse_ok=False)
    citations = [_norm_citation(c) for c in data.get("citations", []) if str(c).strip()]
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return ParsedAnswer(
        answer=str(data.get("answer", "")).strip(),
        citations=citations,
        hierarchy_notes=str(data.get("hierarchy_notes", "")).strip(),
        abstained=bool(data.get("abstained", False)),
        confidence=confidence,
        parse_ok=True,
    )
