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
