from direito_dados.retrieval.evaluate import GoldItem, evaluate

class _R:  # minimal stand-in for Result (only .id used)
    def __init__(self, id): self.id = id

def test_hit_rate_and_mrr():
    gold = [GoldItem("q1", ["A"]), GoldItem("q2", ["Z"])]
    def retriever(q, k):
        return [_R("B"), _R("A")] if q == "q1" else [_R("B"), _R("C")]
    m = evaluate(retriever, gold, k=5)
    assert m["n"] == 2
    assert m["hit_rate"] == 0.5           # q1 hits, q2 misses
    assert abs(m["mrr"] - 0.25) < 1e-9    # q1: 1/2, q2: 0 -> mean 0.25

def test_perfect_retrieval_scores_one():
    gold = [GoldItem("q", ["A"])]
    m = evaluate(lambda q, k: [_R("A")], gold, k=5)
    assert m["hit_rate"] == 1.0 and m["mrr"] == 1.0
