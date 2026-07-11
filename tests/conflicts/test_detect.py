from direito_dados.corpus.models import Article, HierarchyLevel, Norm
from direito_dados.corpus.loader import Corpus
from direito_dados.retrieval.chunks import Chunk
from direito_dados.graph.models import EdgeKind, NormGraph, VerificationState
from direito_dados.generation.llm import FakeLLM
from direito_dados.conflicts.candidates import CandidatePair
from direito_dados.conflicts.detect import Conflict, detect_conflicts, add_conflict_edges

def _setup():
    cp = Norm(id="CP", title="CP", level=HierarchyLevel.DECRETO_LEI,
              articles=[Article("CP","1","c","t"), Article("CP","2","c","t")])
    corpus = Corpus(norms=[cp])
    def ch(id_):
        return Chunk(id=id_, text=id_, embed_text=id_, metadata={
            "norm_id":"CP","article":id_.split("art")[1],"urn":"u","domain":"penal",
            "hierarchy_level":3,"status":"vigente","citation":id_})
    chunks_by_id = {"CP:art1": ch("CP:art1"), "CP:art2": ch("CP:art2")}
    return corpus, chunks_by_id

def test_detect_keeps_high_confidence_conflicts():
    corpus, chunks_by_id = _setup()
    cands = [CandidatePair("CP:art1", "CP:art2", 0.9)]
    llm = FakeLLM('{"conflict": true, "principle": "lex_specialis", "rationale": "r", "confidence": 0.8}')
    conflicts = detect_conflicts(cands, chunks_by_id, corpus, llm, min_confidence=0.5)
    assert len(conflicts) == 1 and isinstance(conflicts[0], Conflict)
    assert conflicts[0].a == "CP:art1" and conflicts[0].principle == "lex_specialis"

def test_detect_drops_low_confidence_and_non_conflicts():
    corpus, chunks_by_id = _setup()
    cands = [CandidatePair("CP:art1", "CP:art2", 0.9)]
    assert detect_conflicts(cands, chunks_by_id, corpus,
                            FakeLLM('{"conflict": true, "confidence": 0.2}'), min_confidence=0.5) == []
    assert detect_conflicts(cands, chunks_by_id, corpus,
                            FakeLLM('{"conflict": false, "confidence": 0.9}'), min_confidence=0.5) == []

def test_add_conflict_edges_are_candidate_state():
    g = NormGraph()
    add_conflict_edges(g, [Conflict("CP:art1", "CP:art2", "lex_specialis", "r", 0.8)])
    edges = g.edges_of_kind(EdgeKind.CONFLICT_CANDIDATE)
    assert len(edges) == 1
    assert edges[0].verification_state == VerificationState.CANDIDATE
    assert edges[0].attrs["principle"] == "lex_specialis"
