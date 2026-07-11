import os

import pytest

pytest.importorskip("chromadb")
from direito_dados.generation.llm import ollama_available, ollama_has_model

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

if not ollama_available() or not ollama_has_model(OLLAMA_MODEL):
    pytest.skip(f"Ollama/{OLLAMA_MODEL} not available", allow_module_level=True)

from direito_dados.corpus import load_corpus, NORMS
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex
from direito_dados.generation.llm import OllamaClient
from direito_dados.conflicts.candidates import generate_candidates
from direito_dados.conflicts.detect import detect_conflicts


def test_pipeline_produces_candidate_conflicts_on_real_cp():
    corpus = load_corpus("data/raw", specs=[NORMS["CP"]])
    chunks = chunk_corpus(corpus)
    e = E5Embedder()
    idx = VectorIndex.build(chunks, e)
    cands = generate_candidates(chunks, idx, e, k=3, threshold=0.85)[:15]
    chunks_by_id = {c.id: c for c in chunks}
    conflicts = detect_conflicts(cands, chunks_by_id, corpus, OllamaClient(model=OLLAMA_MODEL),
                                 min_confidence=0.5)
    # Sanity only: pipeline runs end-to-end and returns a (possibly empty) list of Conflict.
    assert isinstance(conflicts, list)
