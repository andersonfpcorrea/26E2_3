import pytest

pytest.importorskip("chromadb")
from direito_dados.generation.llm import ollama_available

if not ollama_available():
    pytest.skip("Ollama service not running on :11434", allow_module_level=True)

from direito_dados.corpus import load_corpus, NORMS
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.generation.llm import OllamaClient
from direito_dados.generation.rag import answer_question


def test_live_rag_answers_homicide_grounded():
    corpus = load_corpus("data/raw", specs=[NORMS["CP"]])
    idx = VectorIndex.build(chunk_corpus(corpus), E5Embedder())
    valid = {c.id for c in chunk_corpus(corpus)}
    ans = answer_question("qual a pena para quem mata alguém?", idx, E5Embedder(),
                          OllamaClient(model="llama3.1"), k=5, valid_ids=valid)
    assert not ans.abstained
    assert ans.hallucinated_citations == []          # grounded, no invented articles
    assert any("121" in c for c in ans.citations)     # cites homicídio
