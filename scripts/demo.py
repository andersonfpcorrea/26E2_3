"""End-to-end demo of the project: corpus stats, law-as-data analytics, cited
retrieval, and (when Ollama is available) a grounded RAG answer.

Run via ``make demo`` or directly:

    uv run python scripts/demo.py                     # canned demo
    uv run python scripts/demo.py "sua pergunta"      # ask your own question
"""

import sys
import time
from pathlib import Path

# Fallback for running without an installed package (e.g. plain `python scripts/demo.py`).
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from direito_dados.corpus import NORMS, VigenciaStatus, load_corpus
from direito_dados.generation.llm import (
    OllamaClient,
    ollama_available,
    ollama_has_model,
)

MODEL = "llama3.1:8b"
RAW_DIR = str(_repo_root / "data" / "raw")


def _header(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def show_corpus(corpus) -> None:
    _header("1. O corpus — o microssistema penal federal, artigo a artigo")
    articles = corpus.all_articles()
    revoked = sum(1 for a in articles if a.status == VigenciaStatus.REVOGADO)
    print(
        f"{len(corpus.norms)} normas | {len(articles)} artigos | "
        f"{len(corpus.in_force_articles())} em vigor | {revoked} revogados"
    )
    for norm in corpus.norms:
        print(f"  {norm.id:8s} {len(norm.articles):4d} artigos  — {norm.title}")


def show_analytics(corpus) -> None:
    from direito_dados.analytics.timeline import amendments_by_decade
    from direito_dados.graph import build_graph

    _header("2. A lei como dado — quando o Código Penal foi emendado")
    graph = build_graph(corpus)
    cp_only = build_graph(load_corpus(RAW_DIR, specs=[NORMS["CP"]]))
    by_decade = dict(sorted(amendments_by_decade(cp_only).items()))
    print(
        f"Grafo do corpus: {len(graph.nodes)} nós, {len(graph.edges)} arestas "
        f"(emendas, revogações, ...)\n"
    )
    print("Emendas ao Código Penal por década:")
    peak = max(by_decade.values())
    for decade, count in by_decade.items():
        bar = "#" * round(40 * count / peak)
        print(f"  {decade}s {bar} {count}")
    print("\nOs dois picos contam a história: a reforma da Parte Geral de 1984")
    print("(Lei 7.209) e a onda legislativa de 2019-2020 (ex.: 'pacote anticrime').")


def build_index(corpus, quiet: bool = False):
    from direito_dados.retrieval.chunks import chunk_corpus
    from direito_dados.retrieval.embedder import E5Embedder
    from direito_dados.retrieval.index import VectorIndex

    if not quiet:
        _header("3. Busca semântica com filtro de vigência (Código Penal)")
        print("Indexando o Código Penal (na primeira execução, o modelo de embeddings")
        print("multilingual-e5-base, ~440 MB, é baixado automaticamente)...")
    start = time.time()
    cp = load_corpus(RAW_DIR, specs=[NORMS["CP"]])
    chunks = chunk_corpus(cp)
    embedder = E5Embedder()
    index = VectorIndex.build(chunks, embedder)
    print(f"Indexados {len(chunks)} artigos em {time.time() - start:.0f}s.")
    return chunks, embedder, index


def _preview(text: str, limit: int = 58) -> str:
    return " ".join(text.split())[:limit]


def show_retrieval(embedder, index) -> None:
    print('\nConsulta: "qual a pena para quem mata alguém?"')
    for r in index.query("qual a pena para quem mata alguém?", embedder, k=3):
        print(f"  {r.score:.3f}  {r.citation:14s} {_preview(r.text)}...")

    print('\nSegurança de vigência — consulta: "violação sexual mediante fraude":')
    print("  sem filtro (o que a similaridade bruta devolveria):")
    for r in index.query(
        "violação sexual mediante fraude", embedder, k=3, exclude_revoked=False
    ):
        print(f"    {r.score:.3f}  {r.citation:14s} situação: {r.metadata['status']}")
    print("  com filtro (o padrão do sistema):")
    for r in index.query("violação sexual mediante fraude", embedder, k=3):
        print(f"    {r.score:.3f}  {r.citation:14s} situação: {r.metadata['status']}")
    print("  -> os dois primeiros resultados brutos são artigos REVOGADOS; por padrão,")
    print("     normas revogadas nunca são apresentadas como se estivessem em vigor.")


def show_rag(chunks, embedder, index, question: str) -> None:
    from direito_dados.generation.rag import answer_question

    _header("4. Pergunta com resposta fundamentada e citada (RAG local)")
    if not (ollama_available() and ollama_has_model(MODEL)):
        print("Ollama não está ativo (ou o modelo não foi baixado), então esta etapa")
        print("foi pulada. Para habilitar a geração local, rode:  make models")
        print("A busca citada acima e as análises funcionam sem o Ollama.")
        return
    print(f'Pergunta: "{question}"')
    print(f"Gerando com {MODEL} (local")
    answer = answer_question(
        question,
        index,
        embedder,
        OllamaClient(model=MODEL),
        k=5,
        valid_ids={c.id for c in chunks},
    )
    print(f"\nResposta : {answer.answer}")
    print(f"Citações verificadas contra o texto oficial: {answer.citations}")
    print(
        f"Citações alucinadas (inventadas pelo modelo): {answer.hallucinated_citations}"
    )
    if answer.abstained:
        print("O modelo se absteve: não encontrou base suficiente nas normas.")


def main() -> None:
    question = " ".join(sys.argv[1:])
    if question:
        # Ask mode: index quietly and answer the question directly.
        print("Preparando o índice do Código Penal...")
        chunks, embedder, index = build_index(None, quiet=True)
        show_rag(chunks, embedder, index, question)
        return

    corpus = load_corpus(RAW_DIR)
    show_corpus(corpus)
    show_analytics(corpus)
    chunks, embedder, index = build_index(corpus)
    show_retrieval(embedder, index)
    show_rag(chunks, embedder, index, "qual a pena para quem mata alguém?")
    print(
        "\nPara a versão narrada e avaliada de cada etapa, veja as notebooks"
        " c01–c07\ne o relatório em report/. Faça sua própria pergunta com:"
        '  make ask q="..."'
    )


if __name__ == "__main__":
    main()
