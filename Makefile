# Letra da Lei — comandos do projeto
# Requer uv (https://docs.astral.sh/uv/). Alternativa com pip documentada no README.

OLLAMA_MODEL ?= llama3.1:8b

.PHONY: help run setup models ensure-models ensure-data data demo ask test notebooks report app attribution

help: ## mostra esta ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'

run: ## TUDO em um comando: instala o que faltar (verifica antes de baixar) e abre a interface web
	@command -v uv >/dev/null 2>&1 || { \
		echo "uv não encontrado. Instale: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	@echo "[1/4] Dependências Python (uv sync — instantâneo se já instaladas)..."
	@uv sync --all-extras --quiet
	@echo "[2/4] Dados (corpus e autoria já acompanham o repositório; reconstrói só se ausentes)..."
	@$(MAKE) -s ensure-data
	@echo "[3/4] Modelos locais (baixa apenas o que faltar)..."
	@$(MAKE) -s ensure-models
	@echo "[4/4] Abrindo a interface web (Ctrl+C para encerrar)..."
	uv run streamlit run app.py

# Internal: idempotent data provisioning — the snapshots ship committed, so
# these only act when files are genuinely absent.
ensure-data:
	@if [ -f data/raw/CP.txt ]; then echo "  Corpus: presente."; else \
		echo "  Corpus ausente — baixando do Planalto (~1 min)..."; \
		uv run python scripts/fetch_corpus.py; fi
	@if [ -f data/attribution/authorship.json ]; then echo "  Autoria de registro: presente."; else \
		echo "  Dataset de autoria ausente — reconstruindo das APIs do Congresso (~15 min)..."; \
		uv run python scripts/build_attribution.py || \
		echo "  aviso: reconstrução falhou — a aba 'Quem mudou a lei' mostrará instruções."; fi

setup: ## instala todas as dependências Python (uv sync)
	uv sync --all-extras
	@echo "Ambiente pronto. Próximo passo: make run (ou make demo)"

# Internal: idempotent model provisioning — skips anything already present.
ensure-models:
	@if command -v ollama >/dev/null 2>&1; then \
		if ollama list 2>/dev/null | grep -q "^$(OLLAMA_MODEL)"; then \
			echo "  Modelo de geração $(OLLAMA_MODEL): já baixado."; \
		elif ollama list >/dev/null 2>&1; then \
			echo "  Baixando $(OLLAMA_MODEL) (~4,9 GB, uma única vez)..."; \
			ollama pull $(OLLAMA_MODEL) || echo "  aviso: download falhou — o app funciona sem a geração."; \
		else \
			echo "  Ollama instalado, mas o serviço está inativo (abra o app do Ollama"; \
			echo "  ou rode 'ollama serve'). O app funciona sem a geração de respostas."; \
		fi \
	else \
		echo "  Ollama não instalado (https://ollama.com) — opcional: o app funciona"; \
		echo "  sem ele (busca citada, análises e grafo); só a geração de respostas fica off."; \
	fi
	@echo "  Embeddings (multilingual-e5-base): verificando cache (baixa ~440 MB só na 1ª vez)..."
	@uv run python -c "from direito_dados.retrieval.embedder import E5Embedder; \
		E5Embedder().embed_query('ok'); print('  Embeddings prontos.')"

models: ## baixa/verifica os modelos locais (geração via Ollama + embeddings)
	@$(MAKE) -s ensure-models

data: ## (opcional) rebaixa o corpus diretamente do Planalto — um snapshot já acompanha o repo
	uv run python scripts/fetch_corpus.py

demo: ## demonstração no terminal: corpus, análises, busca citada e RAG (se Ollama ativo)
	uv run python scripts/demo.py

ask: ## faça sua pergunta ao RAG: make ask q="qual a pena para furto?"
	@test -n "$(q)" || { echo 'Uso: make ask q="sua pergunta"'; exit 1; }
	uv run python scripts/demo.py "$(q)"

test: ## roda a suíte de testes (166 testes; os que dependem de e5/Ollama pulam se indisponíveis)
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

app: ## abre só a interface web (sem verificar modelos; use make run na primeira vez)
	uv run streamlit run app.py

attribution: ## (opcional) refaz o dataset de autoria a partir das APIs do Congresso — já acompanha o repo
	uv run python scripts/build_attribution.py
