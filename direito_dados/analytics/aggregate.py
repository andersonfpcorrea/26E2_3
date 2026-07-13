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
from direito_dados.generation.llm import LLMClient
from direito_dados.generation.parse import extract_json_object
from direito_dados.graph.models import NormGraph

# Tool names are constrained by a JSON-schema enum in the router call, so the
# model cannot invent a tool — it can only choose one of these or the default.
TOOLS = {
    "maiores_penas": "as maiores penas cominadas no corpus (pena máxima, mais severa/alta/grave)",
    "menores_penas": "as menores penas cominadas (pena mínima, mais branda/leve/baixa/suave)",
    "contagem_corpus": "contagens do corpus (quantos artigos/normas, em vigor, revogados)",
    "mais_alterados": "os dispositivos mais alterados/emendados ao longo do tempo",
    "script_agregado": "outra pergunta agregada/analítica sobre TODAS as normas, sem ferramenta pronta",
    "consulta_especifica": "pergunta sobre um crime/dispositivo/tema específico (caso padrão)",
}

_ROUTER_SYSTEM = (
    "Você é um roteador. Dada uma pergunta sobre a legislação penal brasileira, "
    "escolha a ferramenta certa pelo SIGNIFICADO da pergunta (não por palavras "
    "exatas). Ferramentas:\n"
    + "\n".join(f"- {k}: {v}" for k, v in TOOLS.items())
    + "\nSe a pergunta é sobre um dispositivo, crime ou tema específico "
    "(respondível recuperando alguns artigos), escolha consulta_especifica. "
    'Responda em JSON: {"ferramenta": "..."}.'
)

_ROUTER_SCHEMA = {
    "type": "object",
    "properties": {"ferramenta": {"type": "string", "enum": list(TOOLS)}},
    "required": ["ferramenta"],
}


def route_question(question: str, llm: LLMClient) -> str:
    """Pick a tool semantically; falls back to the default on any parse issue."""
    raw = llm.generate(f"Pergunta: {question}", system=_ROUTER_SYSTEM,
                       format=_ROUTER_SCHEMA)
    data = extract_json_object(raw) or {}
    tool = str(data.get("ferramenta", ""))
    return tool if tool in TOOLS else "consulta_especifica"


def run_tool(tool: str, corpus: Corpus, graph: NormGraph) -> str | None:
    """Execute a preset tool by name; None for non-preset tools."""
    if tool == "maiores_penas":
        return _penas(corpus, lowest=False)
    if tool == "menores_penas":
        return _penas(corpus, lowest=True)
    if tool == "contagem_corpus":
        return _contagem(corpus)
    if tool == "mais_alterados":
        return _mais_alterados(graph)
    return None


def _penas(corpus: Corpus, lowest: bool) -> str | None:
    rows = top_penalties(corpus, n=5, lowest=lowest)
    if not rows:
        return None
    title = ("**Menores penas cominadas no corpus**" if lowest
             else "**Maiores penas cominadas no corpus**")
    lines = [f"{title} (computado sobre todos os artigos em vigor, não gerado por LLM):", ""]
    for citation, _cid, p in rows:
        lines.append(f"- **{citation}** — {p.kind}, de {format_months(p.min_months)} "
                     f"a {format_months(p.max_months)}  \n  _\"{p.excerpt}\"_")
    return "\n".join(lines)


def _contagem(corpus: Corpus) -> str:
    arts = corpus.all_articles()
    revoked = sum(1 for a in arts if a.status == VigenciaStatus.REVOGADO)
    return (f"**Contagem do corpus** (computada): {len(corpus.norms)} normas, "
            f"{len(arts)} artigos — {len(corpus.in_force_articles())} em vigor, "
            f"{revoked} revogados.")


def _mais_alterados(graph: NormGraph) -> str | None:
    rows = most_amended_articles(graph, top=5)
    if not rows:
        return None
    lines = ["**Dispositivos mais alterados** (contagem de emendas/revogações "
             "anotadas pelo Planalto — computado, não gerado):", ""]
    for cid, count in rows:
        lines.append(f"- **{cid.replace(':art', ' art. ')}** — {count} alterações")
    return "\n".join(lines)


def answer_aggregate(question: str, corpus: Corpus, graph: NormGraph) -> str | None:
    """Markdown answer computed over the WHOLE corpus, or None if unsupported."""
    q = question.lower()

    if re.search(r"\b(maior|mais\s+(alta|severa|dura|grave|pesada))\b.{0,30}\bpena\b|\bpena\s+(máxima|maior|mais\s+(severa|dura|grave|pesada|alta))\b", q):
        rows = top_penalties(corpus, n=5)
        if not rows:
            return None
        lines = ["**Maiores penas cominadas no corpus** (computado sobre todos os "
                 "artigos em vigor, não gerado por LLM):", ""]
        for citation, _cid, p in rows:
            lines.append(f"- **{citation}** — {p.kind}, de {format_months(p.min_months)} "
                         f"a {format_months(p.max_months)}  \n  _\"{p.excerpt}\"_")
        return "\n".join(lines)

    if re.search(r"\b(menor|mais\s+(baixa|branda|leve|suave))\b.{0,30}\bpena\b|\bpena\s+(mínima|menor|mais\s+(branda|leve|suave|baixa))\b", q):
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
