from direito_dados.generation.prompt import SYSTEM_PROMPT, build_user_prompt
from direito_dados.retrieval.index import Result


def _r(id_, text, cit):
    return Result(id=id_, text=text, citation=cit, score=0.9,
                  metadata={"status": "vigente", "citation": cit})


def test_system_prompt_sets_guardrails():
    s = SYSTEM_PROMPT.lower()
    assert "json" in s
    assert "não" in s or "nao" in s  # not legal advice / abstention language


def test_user_prompt_includes_ids_texts_and_question():
    results = [_r("CP:art121", "Matar alguém", "CP art. 121")]
    p = build_user_prompt("qual a pena de homicídio?", results)
    assert "[CP:art121]" in p
    assert "Matar alguém" in p
    assert "qual a pena de homicídio?" in p


def test_empty_results_prompt_requests_abstention():
    p = build_user_prompt("pergunta sem base", [])
    assert "abst" in p.lower()
