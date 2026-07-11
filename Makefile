# Letra da Lei — comandos do projeto
# Requer uv (https://docs.astral.sh/uv/). Alternativa com pip documentada no README.

OLLAMA_MODEL ?= llama3.1:8b

.PHONY: help setup models data demo ask test notebooks report app

help: ## mostra esta ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'

setup: ## instala todas as dependências Python (uv sync)
	uv sync --all-extras
	@echo "Ambiente pronto. Próximo passo: make demo"

models: ## baixa o modelo de geração local (Ollama) e o de embeddings
	@command -v ollama >/dev/null 2>&1 || { \
		echo "Ollama não encontrado. Instale em https://ollama.com e rode de novo."; exit 1; }
	ollama pull $(OLLAMA_MODEL)
	@echo "Baixando/aquecendo o modelo de embeddings (multilingual-e5-base, ~440 MB)..."
	uv run python -c "from direito_dados.retrieval.embedder import E5Embedder; \
		E5Embedder().embed_query('ok'); print('Embeddings prontos.')"
	@echo "Modelos prontos. Se o serviço não estiver ativo: ollama serve (ou abra o app)."

data: ## (opcional) rebaixa o corpus diretamente do Planalto — um snapshot já acompanha o repo
	uv run python scripts/fetch_corpus.py

demo: ## demonstração completa: corpus, análises, busca citada e RAG (se Ollama ativo)
	uv run python scripts/demo.py

ask: ## faça sua pergunta ao RAG: make ask q="qual a pena para furto?"
	@test -n "$(q)" || { echo 'Uso: make ask q="sua pergunta"'; exit 1; }
	uv run python scripts/demo.py "$(q)"

test: ## roda a suíte de testes (116 testes; os que dependem de e5/Ollama pulam se indisponíveis)
	uv run pytest -q

notebooks: ## re-executa as 7 notebooks (lento; requer Ollama ativo para c02/c04/c05/c06)
	@for nb in c01_modelos_llm c02_prompting c03_embeddings_busca \
		c04_inferencia_local_ou_remota c05_rag_pipeline c06_antinomias c07_lei_como_dado; do \
		echo "Executando $$nb.ipynb..."; \
		uv run jupyter nbconvert --to notebook --execute --inplace \
			--ExecutePreprocessor.timeout=900 $$nb.ipynb || exit 1; \
	done

report: ## regenera o PDF do relatório a partir de report/relatorio.md
	uv run python scripts/build_report.py

app: ## interface web local (Streamlit) — camada opcional, além da rubrica
	uv run streamlit run app.py
