"""Letra da Lei — optional local Streamlit UI for the criminal-law RAG project.

This is a bonus layer beyond the graded rubric (notebooks c01-c07, report, test
suite). It reuses the `direito_dados.*` package APIs end to end — no logic is
reimplemented here, only presentation. The LLM (Ollama) is only ever called
inside the chat handler and the antinomias adjudication button, never during
the initial page render, so the app boots (and the smoke test passes) even
without Ollama running.

Run via `make app` or `uv run streamlit run app.py`.
"""

from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from direito_dados.analytics.aggregate import answer_aggregate
from direito_dados.analytics.sandbox import build_dataset, generate_and_run
from direito_dados.analytics.authorship import amendments_by_origin, authors_by_party, top_authors
from direito_dados.analytics.network import to_network_data
from direito_dados.analytics.summary import most_amended_articles, vigencia_summary
from direito_dados.analytics.timeline import amendments_by_decade
from direito_dados.attribution.enrich import load_authorship
from direito_dados.attribution.models import Authorship
from direito_dados.conflicts.candidates import CandidatePair, generate_candidates
from direito_dados.conflicts.detect import detect_conflicts
from direito_dados.corpus import NORMS, Corpus, VigenciaStatus, load_corpus
from direito_dados.generation.llm import OllamaClient, ollama_available, ollama_has_model
from direito_dados.generation.rag import RagAnswer, answer_question, is_aggregate_question
from direito_dados.graph import build_graph
from direito_dados.graph.models import NormGraph
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import Result, VectorIndex

MODEL = "llama3.1:8b"
RAW_DIR = str(Path(__file__).resolve().parent / "data" / "raw")
INDEX_DIR = Path(__file__).resolve().parent / "data" / "index"
GRAPH_NODE_CAP = 150
AUTHORSHIP_PATH = Path(__file__).resolve().parent / "data" / "attribution" / "authorship.json"

STATUS_COLORS = {"vigente": "#2e7d32", "alterado": "#f9a825", "revogado": "#9e9e9e"}
NORM_COLOR = "#1565c0"
EXTERNAL_COLOR = "#6a1b9a"


# --- Cached resources -------------------------------------------------------
# Corpus loading and graph building are cheap (pure parsing); the embedding
# cost is paid once ever — the index is persisted in data/index/ and reused
# across sessions (provisioned by `make run` before the UI opens).

@st.cache_resource(show_spinner=False)
def get_corpus(scope: str) -> Corpus:
    """scope: 'full' for all 9 norms, or a norm id (e.g. 'CP') for a single one."""
    specs = None if scope == "full" else [NORMS[scope]]
    return load_corpus(RAW_DIR, specs=specs)


@st.cache_resource(show_spinner=False)
def get_graph(scope: str) -> NormGraph:
    return build_graph(get_corpus(scope))


@st.cache_resource(show_spinner=False)
def get_embedder() -> E5Embedder:
    return E5Embedder()


@st.cache_resource(show_spinner=False)
def get_index_bundle():
    """Full-corpus retrieval bundle backed by the persisted index in data/index/.

    `make run` provisions the index before the UI opens; if it is absent or
    stale (corpus changed), open_or_build rebuilds it here once.
    """
    corpus = get_corpus("full")
    chunks = chunk_corpus(corpus)
    embedder = get_embedder()
    index = VectorIndex.open_or_build(chunks, embedder, persist_dir=str(INDEX_DIR))
    return chunks, embedder, index


@st.cache_resource(show_spinner=False)
def get_flat_dataset():
    """Flattened per-article rows for model-generated aggregation scripts."""
    return build_dataset(get_corpus("full"), get_graph("full"))


@st.cache_resource(show_spinner=False)
def get_authorship() -> list[Authorship] | None:
    """None when `data/attribution/authorship.json` hasn't been generated yet
    (`make attribution`) — the tab renders an info box instead of failing."""
    if not AUTHORSHIP_PATH.exists():
        return None
    return load_authorship(AUTHORSHIP_PATH)


# --- Small rendering helpers -------------------------------------------------

def _preview(text: str, limit: int = 220) -> str:
    return " ".join(text.split())[:limit]


def _badge(label: str, kind: str) -> str:
    colors = {
        "verified": ("#1b5e20", "#c8e6c9"),
        "hallucinated": ("#b71c1c", "#ffcdd2"),
    }
    fg, bg = colors[kind]
    return (
        f'<span style="background-color:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:12px;margin-right:6px;font-size:0.85em;display:inline-block;'
        f'margin-bottom:4px;">{label}</span>'
    )


def _node_color(node: dict) -> str:
    if node["kind"] == "provision":
        return STATUS_COLORS.get(node.get("status"), "#757575")
    if str(node["id"]).startswith("ext:"):
        return EXTERNAL_COLOR
    return NORM_COLOR


def _render_retrieved_expander(results: list[Result]) -> None:
    with st.expander("Dispositivos recuperados"):
        if not results:
            st.write("Nenhum dispositivo recuperado para esta pergunta.")
            return
        for r in results:
            status = r.metadata.get("status", "?")
            st.markdown(f"**{r.citation}** · situação: {status} · score {r.score:.3f}")
            st.caption(_preview(r.text))


# --- Tab 1: Pergunte à lei ---------------------------------------------------

def _render_chat_entry(entry: dict) -> None:
    if entry["mode"] == "computed":
        if entry["computed"]:
            st.markdown(entry["computed"])
            st.caption(
                "Resposta agregada: computada por ferramenta verificada sobre o corpus "
                "inteiro (nenhum texto gerado por LLM)."
            )
        elif entry.get("script_result") is not None and entry["script_result"].ok:
            res = entry["script_result"]
            st.markdown(f"**Resultado (computado sobre o corpus inteiro):**\n\n{res.output}")
            with st.expander("Script gerado pelo modelo (confira o código)"):
                st.code(res.script, language="python")
            st.caption(
                "Sem ferramenta pronta para esta agregação, o modelo local escreveu o "
                "script acima, executado em ambiente restrito **somente sobre os dados** "
                "(sem imports, sem arquivos, sem rede). Audite o código antes de confiar "
                "no número."
            )
        elif entry.get("script_result") is not None:
            st.warning(
                f"O modelo tentou gerar um script para esta agregação, mas a execução "
                f"falhou ({entry['script_result'].error}). Reformule a pergunta ou use "
                "as abas analíticas."
            )
        else:
            st.warning(
                "Pergunta analítica detectada, mas ainda sem ferramenta de agregação "
                "correspondente (e o Ollama está inativo para gerar um script). "
                "Reformule para um dispositivo/tema específico ou use as abas analíticas."
            )
        return
    if entry["mode"] == "rag":
        answer: RagAnswer = entry["answer"]
        if answer.abstained:
            st.warning(f"O modelo se absteve de responder: {answer.answer}")
        else:
            st.markdown(answer.answer)
        if answer.citations:
            st.markdown("**Citações verificadas:**", help="Conferidas por código contra o corpus oficial.")
            st.markdown(" ".join(_badge(c, "verified") for c in answer.citations), unsafe_allow_html=True)
        if answer.hallucinated_citations:
            st.markdown("**Citações alucinadas (descartadas):**")
            st.markdown(
                " ".join(_badge(c, "hallucinated") for c in answer.hallucinated_citations),
                unsafe_allow_html=True,
            )
            st.caption(
                "O modelo citou um id que não existe entre os dispositivos recuperados "
                "para esta pergunta; a citação foi removida da resposta em vez de apresentada "
                "como verificada."
            )
        if answer.quote_status:
            if answer.quote_status == "verificado":
                st.success(
                    f'Trecho de sustentação verificado no dispositivo citado '
                    f'({answer.quote_found_in}): "{answer.quote}"'
                )
            elif answer.quote_status == "atribuicao_incorreta":
                st.error(
                    f"Atribuição incorreta detectada: o trecho que sustenta a resposta "
                    f'pertence a **{answer.quote_found_in}**, não ao dispositivo citado. '
                    f'Trecho: "{answer.quote}"'
                )
            else:
                st.warning(
                    "O trecho de sustentação informado pelo modelo NÃO foi encontrado "
                    "nos dispositivos recuperados — trate a resposta com cautela."
                )
        if answer.hierarchy_notes:
            st.caption(f"Nota de hierarquia: {answer.hierarchy_notes}")
    else:
        st.info(
            "Modo somente recuperação (Ollama indisponível): mostrando os dispositivos mais "
            "relevantes, sem resposta gerada. Para habilitar a geração local, rode `make models` "
            "e garanta que o Ollama esteja ativo."
        )
    _render_retrieved_expander(entry["results"])


def render_qa_tab(ollama_up: bool) -> None:
    st.subheader("Pergunte à lei")
    st.caption(
        "Respostas presas ao texto oficial recuperado; toda citação é verificada por código "
        "e a ausência de base normativa leva à recusa explícita, não à invenção."
    )
    if not ollama_up:
        st.info(
            "Ollama indisponível ou modelo não baixado — as perguntas serão respondidas em "
            "modo somente recuperação (os dispositivos mais relevantes, sem texto gerado). "
            "Rode `make models` para habilitar a geração local."
        )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for entry in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(entry["question"])
        with st.chat_message("assistant"):
            _render_chat_entry(entry)

    question = st.chat_input("Faça sua pergunta sobre a legislação penal...")
    if not question:
        return

    chunks, embedder, index = get_index_bundle()
    entry: dict = {"question": question}
    if is_aggregate_question(question):
        computed = answer_aggregate(question, get_corpus("full"), get_graph("full"))
        entry["mode"] = "computed"
        entry["computed"] = computed
        entry["results"] = []
        if computed is None and ollama_up:
            # Tier 2: no preset tool covers it — the model writes a script that
            # runs over the data only, in a restricted subprocess, and the
            # generated code is shown for audit.
            with st.spinner("Sem ferramenta pronta para esta agregação — gerando e "
                            "executando um script sobre os dados (local)..."):
                entry["script_result"] = generate_and_run(
                    question, get_flat_dataset(), OllamaClient(model=MODEL), retries=2)
        st.session_state.chat_history.append(entry)
        st.rerun()
    if ollama_up:
        llm = OllamaClient(model=MODEL)
        valid_ids = {c.id for c in chunks}
        with st.spinner(f"Gerando com {MODEL} (local)..."):
            answer = answer_question(question, index, embedder, llm, k=5, valid_ids=valid_ids,
                                     verify_quote=True)
        entry["mode"] = "rag"
        entry["answer"] = answer
        entry["results"] = index.query(question, embedder, k=5)
    else:
        entry["mode"] = "retrieval"
        entry["results"] = index.query(question, embedder, k=5)

    st.session_state.chat_history.append(entry)
    st.rerun()


# --- Tab 2: A lei no tempo ----------------------------------------------------

def render_timeline_tab() -> None:
    st.subheader("A lei no tempo")
    st.caption("As emendas e revogações anotadas pelo Planalto, agregadas por década.")

    options = ["Todas as normas"] + sorted(NORMS.keys())
    choice = st.selectbox("Norma", options, key="timeline_norm")
    scope = "full" if choice == "Todas as normas" else choice
    graph = get_graph(scope)

    by_decade = amendments_by_decade(graph)
    if not by_decade:
        st.info("Nenhuma emenda registrada para esta seleção.")
        return

    decades = sorted(by_decade)
    min_d, max_d = decades[0], decades[-1]
    if min_d == max_d:
        lo, hi = min_d, max_d
        st.caption(f"Única década com emendas: {min_d}s.")
    else:
        lo, hi = st.slider(
            "Intervalo de décadas", min_value=min_d, max_value=max_d,
            value=(min_d, max_d), step=10,
        )

    filtered = {d: c for d, c in by_decade.items() if lo <= d <= hi}
    chart_df = pd.DataFrame(
        {"emendas": [filtered.get(d, 0) for d in sorted(filtered)]},
        index=[f"{d}s" for d in sorted(filtered)],
    )
    st.bar_chart(chart_df)

    st.subheader("Artigos mais emendados")
    top_n = st.slider("Quantidade", 5, 30, 10, key="timeline_top_n")
    ranked = most_amended_articles(graph, top=top_n)
    rows = [
        {"citação": (graph.node(pid).label if graph.node(pid) else pid), "emendas": count}
        for pid, count in ranked
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# --- Tab 3: O grafo ------------------------------------------------------------

def render_graph_tab() -> None:
    st.subheader("O grafo")
    st.caption(
        "Nós e arestas do grafo normativo (normas, dispositivos, emendas e revogações), "
        "construído a partir das anotações oficiais do Planalto."
    )

    norm_ids = sorted(NORMS.keys())
    norm_id = st.selectbox("Norma", norm_ids, index=norm_ids.index("CP"), key="graph_norm")
    graph = get_graph(norm_id)
    data = to_network_data(graph, include_external=True)
    nodes, edges = data["nodes"], data["edges"]

    kind_counts = Counter(n["kind"] for n in nodes)
    edge_kind_counts = Counter(e["kind"] for e in edges)
    stat_cols = st.columns(4)
    stat_cols[0].metric("Nós", len(nodes))
    stat_cols[1].metric("Arestas", len(edges))
    stat_cols[2].metric("Normas", kind_counts.get("norm", 0))
    stat_cols[3].metric("Dispositivos", kind_counts.get("provision", 0))
    st.caption(
        "Arestas por tipo: " + ", ".join(f"{k}={v}" for k, v in sorted(edge_kind_counts.items()))
    )

    capped_nodes = nodes[:GRAPH_NODE_CAP]
    kept_ids = {n["id"] for n in capped_nodes}
    capped_edges = [e for e in edges if e["src"] in kept_ids and e["dst"] in kept_ids]
    if len(nodes) > GRAPH_NODE_CAP:
        st.caption(
            f"Mostrando os primeiros {GRAPH_NODE_CAP} nós de {len(nodes)} (limite para "
            "manter a legibilidade do grafo interativo)."
        )

    st.markdown(
        " ".join([
            _badge("dispositivo vigente", "verified"),
            f'<span style="background-color:#f9a825;color:#3e2700;padding:2px 10px;'
            f'border-radius:12px;margin-right:6px;font-size:0.85em;">dispositivo alterado</span>',
            f'<span style="background-color:#9e9e9e;color:#212121;padding:2px 10px;'
            f'border-radius:12px;margin-right:6px;font-size:0.85em;">dispositivo revogado</span>',
            f'<span style="background-color:#1565c0;color:white;padding:2px 10px;'
            f'border-radius:12px;margin-right:6px;font-size:0.85em;">norma</span>',
            f'<span style="background-color:#6a1b9a;color:white;padding:2px 10px;'
            f'border-radius:12px;margin-right:6px;font-size:0.85em;">lei externa (emenda)</span>',
        ]),
        unsafe_allow_html=True,
    )

    net = Network(height="650px", width="100%", directed=True, cdn_resources="in_line")
    net.toggle_physics(True)
    for n in capped_nodes:
        net.add_node(
            n["id"], label=n["label"],
            title=f"{n['kind']} · {n.get('status') or ''}",
            color=_node_color(n),
        )
    for e in capped_edges:
        net.add_edge(e["src"], e["dst"], title=e["kind"])
    components.html(net.generate_html(notebook=False), height=670, scrolling=True)


# --- Tab 4: Antinomias ---------------------------------------------------------

@st.cache_data(show_spinner=False)
def _candidates_for(threshold: float, _chunks, _index, _embedder) -> list[CandidatePair]:
    return generate_candidates(_chunks, _index, _embedder, k=5, threshold=threshold)


def render_conflicts_tab(ollama_up: bool) -> None:
    st.subheader("Antinomias")
    st.warning(
        "Os pares abaixo são **candidatos** a antinomia, obtidos por similaridade semântica "
        "(e, se adjudicados, por um LLM local). Nada aqui é um veredito jurídico — todo "
        "candidato é matéria para revisão humana."
    )

    chunks, embedder, index = get_index_bundle()
    corpus = get_corpus("full")
    chunks_by_id = {c.id: c for c in chunks}

    threshold = st.slider("Limiar de similaridade", 0.50, 0.99, 0.85, 0.01)
    with st.spinner("Buscando pares candidatos por similaridade..."):
        candidates = _candidates_for(threshold, chunks, index, embedder)

    if not candidates:
        st.info("Nenhum par candidato acima do limiar selecionado.")
        return

    st.dataframe(
        pd.DataFrame([{"a": c.a, "b": c.b, "similaridade": round(c.similarity, 4)} for c in candidates]),
        width="stretch", hide_index=True,
    )

    st.markdown("#### Ler os dois dispositivos lado a lado")
    pair_labels = [f"{c.a}  ×  {c.b}   (similaridade {c.similarity:.3f})"
                   for c in candidates[:50]]
    chosen = st.selectbox("Par candidato", pair_labels, key="conflict_pair_reader")
    pair = candidates[pair_labels.index(chosen)]
    col_a, col_b = st.columns(2)
    for col, cid in ((col_a, pair.a), (col_b, pair.b)):
        chunk = chunks_by_id.get(cid)
        with col, st.container(border=True):
            if chunk is None:
                st.warning(f"{cid}: texto não encontrado no índice.")
                continue
            st.markdown(f"**{chunk.metadata.get('citation', cid)}**")
            if chunk.metadata.get("rubrica"):
                st.caption(f"Rubrica: {chunk.metadata['rubrica']}")
            st.caption(f"Situação: {chunk.metadata.get('status', '?')}")
            st.markdown(chunk.text)

    st.markdown("---")
    col_n, col_btn = st.columns([1, 3])
    with col_n:
        top_n = st.number_input("N", min_value=1, max_value=min(20, len(candidates)), value=min(5, len(candidates)))
    with col_btn:
        adjudicate_clicked = st.button(
            "Adjudicar top-N com o LLM local", disabled=not ollama_up,
        )
    if not ollama_up:
        st.caption("Indisponível: Ollama não está ativo ou o modelo não foi baixado (`make models`).")

    if adjudicate_clicked:
        llm = OllamaClient(model=MODEL)
        with st.spinner(f"Adjudicando {top_n} par(es) com {MODEL}..."):
            conflicts = detect_conflicts(candidates[: int(top_n)], chunks_by_id, corpus, llm)
        if not conflicts:
            st.info("Nenhum candidato foi confirmado como conflito plausível pelo modelo.")
        for conflict in conflicts:
            with st.container(border=True):
                st.markdown(f"**{conflict.a}** × **{conflict.b}** — princípio: `{conflict.principle}`")
                st.write(conflict.rationale)
                st.caption(f"Confiança: {conflict.confidence:.2f} · candidato, não veredito")


# --- Tab 5: Vigência -------------------------------------------------------------

def render_vigencia_tab() -> None:
    st.subheader("Vigência")
    full_corpus = get_corpus("full")

    summary = vigencia_summary(full_corpus)
    order = ["vigente", "alterado", "revogado"]
    summary_df = pd.DataFrame(summary).T[order]
    st.dataframe(summary_df, width="stretch")

    st.subheader("Artigos revogados")
    rows = []
    for norm in full_corpus.norms:
        for art in norm.articles:
            if art.status != VigenciaStatus.REVOGADO:
                continue
            revoking = next((a for a in art.annotations if a.kind == "revogado"), None)
            rows.append({
                "norma": norm.id,
                "artigo": art.number,
                "citação": art.citation,
                "lei revogadora": revoking.law_ref if revoking else "",
                "ano": revoking.year if revoking else None,
            })
    revoked_df = pd.DataFrame(rows)
    search = st.text_input("Buscar (norma, artigo, lei revogadora)...", key="vigencia_search")
    if search and not revoked_df.empty:
        mask = revoked_df.apply(
            lambda row: search.lower() in " ".join(str(v) for v in row).lower(), axis=1
        )
        revoked_df = revoked_df[mask]
    st.dataframe(revoked_df, width="stretch", hide_index=True)


# --- Tab 6: Quem mudou a lei -------------------------------------------------------

def _authorship_row(record: Authorship) -> dict:
    autores = ", ".join(
        f"{a.name} ({a.party})" if a.party else a.name for a in record.authors
    )
    return {
        "lei": record.law_ref,
        "ano": record.ano,
        "status": record.status,
        "projeto de origem": record.origin_bill,
        "casa": record.origin_house,
        "autores": autores,
        "fonte": record.source,
    }


def render_attribution_tab() -> None:
    st.subheader("Quem mudou a lei")
    records = get_authorship()
    if records is None:
        st.info(
            "Dataset de autoria ainda não gerado. Rode `make attribution` "
            "(ou `uv run python scripts/build_attribution.py`) para resolvê-lo "
            "a partir dos dados abertos do Congresso — a execução completa "
            "leva de 10 a 15 minutos e o resultado fica salvo em "
            "`data/attribution/authorship.json`."
        )
        return

    st.caption(
        "Autoria de registro, conforme os dados abertos do Congresso — "
        "proveniência factual, não atribuição de responsabilidade."
    )
    st.warning(
        "**Nuance do pacote anticrime (Lei nº 13.964/2019):** a autoria oficial "
        "credita 11 deputados signatários do PL 10.372/2018; o projeto do "
        "Poder Executivo (PL 882/2019) foi arquivado por prejudicialidade "
        "após ser absorvido pelo substitutivo, e não consta como coautor de "
        "registro — ainda que seja a versão popularmente associada à lei.\n\n"
        "**Partido = filiação atual/última registrada**, não necessariamente "
        "a filiação no momento da autoria (troca-troca partidário é comum)."
    )

    by_tipo: dict[str, Counter] = {}
    for r in records:
        by_tipo.setdefault(r.tipo or "(sem tipo)", Counter())[r.status] += 1

    st.subheader("Cobertura")
    coverage_rows = [
        {"tipo": tipo, "status": status, "quantidade": count}
        for tipo, counts in sorted(by_tipo.items())
        for status, count in sorted(counts.items())
    ]
    st.dataframe(pd.DataFrame(coverage_rows), width="stretch", hide_index=True)

    col_origin, col_party = st.columns(2)
    with col_origin:
        st.markdown("**Amendas/leis por origem**")
        origin_counts = amendments_by_origin(records)
        if origin_counts:
            st.bar_chart(pd.Series(origin_counts, name="quantidade"))
        else:
            st.caption("Sem registros resolvidos para agregar.")
    with col_party:
        st.markdown("**Autores parlamentares por partido**")
        party_counts = authors_by_party(records)
        if party_counts:
            st.bar_chart(pd.Series(party_counts, name="quantidade"))
        else:
            st.caption("Sem autores parlamentares identificados.")

    st.subheader("Autores mais frequentes")
    top_n = st.slider("Quantidade", 5, 30, 15, key="attribution_top_n")
    ranked = top_authors(records, top=top_n)
    st.dataframe(
        pd.DataFrame(ranked, columns=["autor", "leis de autoria"]),
        width="stretch", hide_index=True,
    )

    st.subheader("Todas as normas")
    table_df = pd.DataFrame([_authorship_row(r) for r in records])
    search = st.text_input("Buscar (lei, autor, partido, projeto de origem)...", key="attribution_search")
    if search and not table_df.empty:
        mask = table_df.apply(
            lambda row: search.lower() in " ".join(str(v) for v in row).lower(), axis=1
        )
        table_df = table_df[mask]
    st.dataframe(table_df, width="stretch", hide_index=True)


# --- Main ------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Letra da Lei", page_icon="⚖️", layout="wide")
    st.title("Letra da Lei")
    st.caption(
        "Pesquisa e compreensão da legislação penal federal brasileira — RAG local com "
        "citações verificadas, e a lei como dado."
    )
    st.warning(
        "Ferramenta de pesquisa e compreensão da legislação; **não constitui aconselhamento "
        "jurídico**. Antinomias detectadas são apresentadas como **candidatas para revisão "
        "humana**, nunca como veredito."
    )

    with st.sidebar:
        st.header("Status")
        st.caption("Índice semântico: as 9 normas do microssistema (persistido em disco).")
        ollama_up = ollama_available() and ollama_has_model(MODEL)
        st.caption(f"Ollama ({MODEL}): {'ativo' if ollama_up else 'indisponível'}")

    with st.spinner(
        "Carregando o índice semântico (reconstrói aqui apenas se ausente — use "
        "`make run` para provisionar antes de abrir)..."
    ):
        get_index_bundle()

    tab_qa, tab_timeline, tab_graph, tab_conflicts, tab_vigencia, tab_attribution = st.tabs(
        ["Pergunte à lei", "A lei no tempo", "O grafo", "Antinomias", "Vigência", "Quem mudou a lei"]
    )
    with tab_qa:
        render_qa_tab(ollama_up)
    with tab_timeline:
        render_timeline_tab()
    with tab_graph:
        render_graph_tab()
    with tab_conflicts:
        render_conflicts_tab(ollama_up)
    with tab_vigencia:
        render_vigencia_tab()
    with tab_attribution:
        render_attribution_tab()


main()
