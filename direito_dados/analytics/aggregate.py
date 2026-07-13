"""Deterministic answers for aggregate questions the RAG cannot answer.

Top-k retrieval cannot compute max/count/compare-all — but the structured
layer can, exactly and with provenance. These vetted tools replace an LLM
guessing from fragments: no generated code is executed (by design — model-
written code would be an injection surface in a legal tool).
"""

import re

from direito_dados.corpus.loader import Corpus
from direito_dados.corpus.models import VigenciaStatus
from direito_dados.analytics.penalties import format_months, top_penalties
from direito_dados.analytics.summary import most_amended_articles
from direito_dados.graph.models import NormGraph


def answer_aggregate(question: str, corpus: Corpus, graph: NormGraph) -> str | None:
    """Markdown answer computed over the WHOLE corpus, or None if unsupported."""
    q = question.lower()

    if re.search(r"\b(maior|mais\s+alta?)\b.{0,30}\bpena\b|\bpena\s+(máxima|maior)\b", q):
        rows = top_penalties(corpus, n=5)
        if not rows:
            return None
        lines = ["**Maiores penas cominadas no corpus** (computado sobre todos os "
                 "artigos em vigor, não gerado por LLM):", ""]
        for citation, _cid, p in rows:
            lines.append(f"- **{citation}** — {p.kind}, de {format_months(p.min_months)} "
                         f"a {format_months(p.max_months)}  \n  _\"{p.excerpt}\"_")
        return "\n".join(lines)

    if re.search(r"\b(menor|mais\s+baixa?)\b.{0,30}\bpena\b|\bpena\s+mínima\b", q):
        rows = top_penalties(corpus, n=5, lowest=True)
        if not rows:
            return None
        lines = ["**Menores penas cominadas no corpus** (computado, não gerado):", ""]
        for citation, _cid, p in rows:
            lines.append(f"- **{citation}** — {p.kind}, de {format_months(p.min_months)} "
                         f"a {format_months(p.max_months)}  \n  _\"{p.excerpt}\"_")
        return "\n".join(lines)

    if re.search(r"quant[oa]s\b.{0,30}\b(artigos?|dispositivos?|normas?|leis)\b", q):
        arts = corpus.all_articles()
        revoked = sum(1 for a in arts if a.status == VigenciaStatus.REVOGADO)
        return (f"**Contagem do corpus** (computada): {len(corpus.norms)} normas, "
                f"{len(arts)} artigos — {len(corpus.in_force_articles())} em vigor, "
                f"{revoked} revogados.")

    if re.search(r"mais\s+(alterad|emendad|modificad)", q):
        rows = most_amended_articles(graph, top=5)
        if not rows:
            return None
        lines = ["**Dispositivos mais alterados** (contagem de emendas/revogações "
                 "anotadas pelo Planalto — computado, não gerado):", ""]
        for cid, count in rows:
            lines.append(f"- **{cid.replace(':art', ' art. ')}** — {count} alterações")
        return "\n".join(lines)

    return None
