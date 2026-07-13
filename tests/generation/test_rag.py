import pytest
pytest.importorskip("chromadb")

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import FakeEmbedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.generation.llm import FakeLLM
from direito_dados.generation.rag import RagAnswer, answer_question

def _chunks():
    def c(id_, text, status="vigente"):
        return Chunk(id=id_, text=text, metadata={
            "norm_id":"CP","article":id_.split("art")[1],"urn":"urn:x","domain":"penal",
            "hierarchy_level":3,"status":status,"citation":id_})
    return [c("CP:art121","Matar alguém"), c("CP:art155","Subtrair coisa"),
            c("CP:art240","Adultério", status="revogado")]

def _index():
    return VectorIndex.build(_chunks(), FakeEmbedder())

def test_grounded_answer_keeps_valid_citation():
    e = FakeEmbedder()
    llm = FakeLLM('{"answer":"Matar alguém é homicídio.","citations":["CP:art121"],"hierarchy_notes":"","abstained":false,"confidence":0.9}')
    ans = answer_question("o que é homicídio?", _index(), e, llm, k=3)
    assert isinstance(ans, RagAnswer)
    assert "CP:art121" in ans.citations
    assert ans.hallucinated_citations == []
    assert not ans.abstained

def test_hallucinated_citation_is_flagged():
    e = FakeEmbedder()
    llm = FakeLLM('{"answer":"...","citations":["CP:art999"],"hierarchy_notes":"","abstained":false,"confidence":0.7}')
    ans = answer_question("pergunta", _index(), e, llm, k=3)
    assert ans.hallucinated_citations == ["CP:art999"]
    assert "CP:art999" not in ans.citations

def test_empty_retrieval_abstains_without_calling_model():
    e = FakeEmbedder()
    llm = FakeLLM('{"answer":"não deveria ser chamado"}')
    ans = answer_question("xyz", VectorIndex.build([], e), e, llm, k=3)
    assert ans.abstained and ans.citations == [] and llm.last_prompt is None


def _quoted_llm(quote, citations):
    import json
    return FakeLLM(json.dumps({
        "trecho_citado": quote, "answer": "resposta",
        "citations": citations, "abstained": False, "confidence": 0.9,
    }))


def test_quote_verified_when_excerpt_is_in_cited_article():
    e = FakeEmbedder()
    llm = _quoted_llm("Matar alguém", ["CP:art121"])
    ans = answer_question("o que é homicídio?", _index(), e, llm, k=3, verify_quote=True)
    assert ans.quote_status == "verificado"
    assert ans.quote_found_in == "CP:art121"


def test_quote_misattribution_is_flagged_with_real_owner():
    e = FakeEmbedder()
    # Model cites art121 but quotes art155's text — the content/citation
    # mismatch that plain id verification cannot catch.
    llm = _quoted_llm("Subtrair coisa", ["CP:art121"])
    ans = answer_question("pergunta", _index(), e, llm, k=3, verify_quote=True)
    assert ans.quote_status == "atribuicao_incorreta"
    assert ans.quote_found_in == "CP:art155"


def test_quote_not_found_when_fabricated():
    e = FakeEmbedder()
    llm = _quoted_llm("texto que não existe em lugar nenhum", ["CP:art121"])
    ans = answer_question("pergunta", _index(), e, llm, k=3, verify_quote=True)
    assert ans.quote_status == "nao_encontrado"


def test_default_path_has_no_quote_fields():
    e = FakeEmbedder()
    llm = FakeLLM('{"answer":"x","citations":["CP:art121"],"abstained":false,"confidence":0.9}')
    ans = answer_question("pergunta", _index(), e, llm, k=3)
    assert ans.quote == "" and ans.quote_status == ""
