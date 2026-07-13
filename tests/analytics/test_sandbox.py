"""Tests for the restricted script runner and dataset flattening."""

import json

from direito_dados.analytics.sandbox import build_dataset, generate_and_run, run_script
from direito_dados.corpus.loader import Corpus
from direito_dados.corpus.models import Article, HierarchyLevel, Norm
from direito_dados.generation.llm import FakeLLM
from direito_dados.graph.models import NormGraph


def _dataset():
    cp = Norm(id="CP", title="CP", level=HierarchyLevel.LEI_ORDINARIA, articles=[
        Article("CP", "121", "Matar alguém", "Matar alguém: Pena - reclusão, de seis a vinte anos.",
                rubrica="Homicídio simples"),
        Article("CP", "155", "Subtrair", "Subtrair: Pena - reclusão, de um a quatro anos."),
    ])
    return build_dataset(Corpus(norms=[cp]), NormGraph())


def test_dataset_rows_have_flat_fields():
    rows = _dataset()
    assert rows[0]["citacao"] == "CP art. 121"
    assert rows[0]["pena_max_meses"] == 240
    assert rows[0]["rubrica"] == "Homicídio simples"
    assert rows[1]["pena_min_meses"] == 12


def test_run_script_computes_over_data():
    res = run_script(
        "com_pena = [a for a in artigos if a['pena_max_meses']]\n"
        "resultado = max(com_pena, key=lambda a: a['pena_max_meses'])['citacao']",
        _dataset())
    assert res.ok and res.output == "CP art. 121"


def test_run_script_blocks_imports_and_reports_error():
    res = run_script("import os\nresultado = 'x'", _dataset())
    assert not res.ok
    assert "import" in res.error.lower() or "Error" in res.error


def test_run_script_survives_bad_code():
    res = run_script("resultado = artigos[999]['citacao']", _dataset())
    assert not res.ok


def test_generate_and_run_with_retry():
    good = json.dumps({"script": "resultado = len(artigos)"})
    bad = json.dumps({"script": "resultado = 1/0"})
    calls = iter([bad, good])
    llm = FakeLLM(lambda prompt, system: next(calls))
    res = generate_and_run("quantos artigos?", _dataset(), llm)
    assert res.ok and res.output == "2"


def test_script_that_never_assigns_resultado_fails():
    res = run_script("def f(artigos):\n    resultado = 1\n", _dataset())
    assert not res.ok and "resultado" in res.error
