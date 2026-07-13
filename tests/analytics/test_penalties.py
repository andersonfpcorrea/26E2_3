"""Tests for penalty extraction and aggregate answering."""

from direito_dados.analytics.aggregate import answer_aggregate
from direito_dados.analytics.penalties import extract_penalties, format_months, top_penalties
from direito_dados.corpus.loader import Corpus
from direito_dados.corpus.models import Article, HierarchyLevel, Norm
from direito_dados.graph.models import NormGraph


def test_extracts_digit_and_word_ranges():
    pens = extract_penalties("Pena - reclusão, de 2 (dois) a 6 (seis) anos.")
    assert pens[0].kind == "reclusão"
    assert (pens[0].min_months, pens[0].max_months) == (24, 72)
    pens = extract_penalties("Pena - detenção, de um a quatro anos, e multa.")
    assert (pens[0].min_months, pens[0].max_months) == (12, 48)


def test_extracts_months_and_multiple_clauses():
    text = ("Pena - detenção, de três meses a um ano.\n"
            "§ 1º Pena - reclusão, de doze a trinta anos.")
    pens = extract_penalties(text)
    assert (pens[0].min_months, pens[0].max_months) == (3, 12)
    assert (pens[1].min_months, pens[1].max_months) == (144, 360)


def test_no_penalty_no_match():
    assert extract_penalties("Este artigo não comina pena alguma.") == []


def _corpus():
    def art(n, text):
        return Article(norm_id="CP", number=n, caput=text[:30], text=text)
    cp = Norm(id="CP", title="CP", level=HierarchyLevel.LEI_ORDINARIA, articles=[
        art("121", "Matar alguém: Pena - reclusão, de seis a vinte anos."),
        art("155", "Subtrair: Pena - reclusão, de um a quatro anos."),
        art("159", "Sequestrar: Pena - reclusão, de vinte e quatro a trinta anos."
                    " Pena - reclusão, de 24 (vinte e quatro) a 30 (trinta) anos."),
    ])
    return Corpus(norms=[cp])


def test_top_penalties_ranks_by_max():
    rows = top_penalties(_corpus(), n=2)
    assert rows[0][0] == "CP art. 159"


def test_answer_aggregate_maior_pena_and_counts():
    c = _corpus()
    g = NormGraph()
    out = answer_aggregate("qual a lei com a maior pena?", c, g)
    assert out and "CP art. 159" in out and "computado" in out
    out2 = answer_aggregate("quantos artigos existem?", c, g)
    assert out2 and "3 artigos" in out2
    assert answer_aggregate("pergunta comum sobre furto", c, g) is None


def test_format_months():
    assert format_months(72) == "6 anos"
    assert format_months(3) == "3 meses"


def test_penalty_synonyms_route_to_preset_tools():
    c = _corpus()
    g = NormGraph()
    assert "Menores penas" in answer_aggregate("qual a lei com a pena mais branda?", c, g)
    assert "Menores penas" in answer_aggregate("qual crime tem a pena mais leve?", c, g)
    assert "Maiores penas" in answer_aggregate("qual a pena mais severa do código?", c, g)
