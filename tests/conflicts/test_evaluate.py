from direito_dados.conflicts.evaluate import GoldAntinomy, evaluate_antinomias
from direito_dados.conflicts.detect import Conflict

def _c(a, b): return Conflict(a, b, "p", "r", 0.9)

def test_precision_recall_f1():
    detected = [_c("CP:art1", "CP:art2"), _c("CP:art3", "CP:art9")]   # 1 correct, 1 wrong
    gold = [GoldAntinomy("CP:art2", "CP:art1"), GoldAntinomy("CP:art5", "CP:art6")]  # note reversed order
    m = evaluate_antinomias(detected, gold)
    assert m["tp"] == 1 and m["fp"] == 1 and m["fn"] == 1
    assert m["precision"] == 0.5 and m["recall"] == 0.5
    assert abs(m["f1"] - 0.5) < 1e-9

def test_empty_inputs_do_not_crash():
    m = evaluate_antinomias([], [])
    assert m["precision"] == 0.0 and m["recall"] == 0.0 and m["f1"] == 0.0
