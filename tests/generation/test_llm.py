from direito_dados.generation.llm import FakeLLM, LLMClient


def test_fakellm_returns_static_string_and_records_prompt():
    llm = FakeLLM("resposta fixa")
    out = llm.generate("pergunta", system="sys")
    assert out == "resposta fixa"
    assert llm.last_prompt == "pergunta" and llm.last_system == "sys"


def test_fakellm_supports_callable():
    llm = FakeLLM(lambda prompt, system: f"echo:{prompt}")
    assert llm.generate("oi") == "echo:oi"


def test_fakellm_satisfies_protocol():
    assert isinstance(FakeLLM("x"), LLMClient)
