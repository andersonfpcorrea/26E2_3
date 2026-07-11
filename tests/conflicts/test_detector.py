from direito_dados.generation.llm import FakeLLM
from direito_dados.conflicts.detector import ConflictVerdict, adjudicate, build_conflict_prompt

def test_prompt_includes_both_provisions_and_hint():
    p = build_conflict_prompt("Matar alguém", "CP art. 121", "Homicídio qualificado",
                              "L8072 art. 1", "hint: lex posterior")
    assert "Matar alguém" in p and "Homicídio qualificado" in p and "hint: lex posterior" in p

def test_adjudicate_parses_conflict_verdict():
    llm = FakeLLM('{"conflict": true, "principle": "lex_specialis", "rationale": "sobreposição", "confidence": 0.8}')
    v = adjudicate("a", "CP art. 1", "b", "CP art. 2", "hint", llm)
    assert isinstance(v, ConflictVerdict)
    assert v.conflict is True and v.principle == "lex_specialis" and v.confidence == 0.8

def test_adjudicate_fails_safe_to_no_conflict():
    v = adjudicate("a", "c1", "b", "c2", "hint", FakeLLM("não sei responder em json"))
    assert v.conflict is False and v.confidence == 0.0
