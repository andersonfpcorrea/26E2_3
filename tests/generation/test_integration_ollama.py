import os

import pytest

pytest.importorskip("chromadb")
from direito_dados.generation.llm import ollama_available, ollama_has_model

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

if not ollama_available() or not ollama_has_model(OLLAMA_MODEL):
    pytest.skip(f"Ollama/{OLLAMA_MODEL} not available on :11434", allow_module_level=True)

from direito_dados.corpus import load_corpus, NORMS
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.generation.llm import OllamaClient
from direito_dados.generation.rag import answer_question


def test_live_rag_answers_homicide_grounded():
    corpus = load_corpus("data/raw", specs=[NORMS["CP"]])
    chunks = chunk_corpus(corpus)
    embedder = E5Embedder()
    idx = VectorIndex.build(chunks, embedder)
    valid = {c.id for c in chunks}
    ans = answer_question("qual a pena para quem mata alguém?", idx, embedder,
                          OllamaClient(model=OLLAMA_MODEL), k=5, valid_ids=valid)
    # Grounding: homicídio is retrieved, no invented citations survive verification.
    assert "CP:art121" in ans.retrieved_ids
    assert ans.hallucinated_citations == []
