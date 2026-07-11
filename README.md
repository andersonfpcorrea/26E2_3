# O Direito como Dado

Um sistema que permite **conversar com a legislação penal federal brasileira** — com
respostas fundamentadas no texto oficial, citações verificadas automaticamente e recusa
explícita quando não há base legal — e que trata **a própria lei como dado**: mostra como
ela cresceu, o que está em vigor, o que foi revogado e onde duas normas podem se contradizer.

> **Aviso:** ferramenta de *pesquisa e compreensão* da legislação. Não constitui consulta,
> parecer ou aconselhamento jurídico. Conflitos entre normas são apresentados como
> **candidatos para revisão humana**, nunca como veredito.

**Disciplina:** Sistemas Cognitivos com Large Language Models (INFNET, 26E2_3) ·
**Autor:** Anderson Felipe Paixão Corrêa

---

## O que este sistema faz

**1. Responde perguntas sobre a lei, citando o texto oficial** (exemplo real, gerado
localmente com Llama 3.1 8B):

```text
Pergunta : Qual a pena para o funcionário público que se apropria de
           dinheiro público em razão do cargo?

Resposta : Pena - reclusão, de dois a doze anos.
Citações verificadas contra o texto oficial: [CP art. 312 — peculato]
Citações inventadas pelo modelo (alucinadas): nenhuma
```

Toda citação que o modelo produz é conferida, por código, contra o corpus oficial: citação
inexistente é sinalizada como **alucinada** e descartada; sem base recuperada, o sistema
**se recusa a responder** em vez de inventar.

**2. Nunca apresenta lei revogada como se estivesse em vigor.** Cada artigo carrega sua
situação de vigência (em vigor / alterado / revogado), extraída das anotações oficiais do
Planalto, e a busca exclui normas revogadas por padrão. Exemplo real: para *"violação
sexual mediante fraude"*, os dois resultados mais similares são artigos **revogados**
(arts. 214 e 216 do CP) — o sistema os filtra antes de qualquer resposta.

**3. Revela a estrutura e a história da lei.** As 4.453 emendas do corpus viram um grafo e
uma linha do tempo — os picos de 1984 (reforma da Parte Geral) e de 2019–2020 ("pacote
anticrime") aparecem nos dados — e um detector aponta **candidatos a antinomia** (normas
possivelmente conflitantes), classificados pelos critérios clássicos de resolução
(*lex superior, lex specialis, lex posterior* — LINDB).

## Comece em 3 comandos

Requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) (gerenciador
Python; instala o próprio Python 3.13 se preciso). Opcional: [Ollama](https://ollama.com)
para a geração local.

```bash
make setup     # instala todas as dependências (uv sync)
make demo      # corpus, análises e busca citada — funciona sem Ollama
make models    # (opcional) baixa os modelos locais e habilita as respostas geradas
```

Depois, pergunte o que quiser: `make ask q="qual a pena para furto?"`
Todos os comandos: `make help`. Alternativa sem uv no final deste arquivo.

## Entregáveis e mapa da avaliação

Os três artefatos da entrega e onde cada competência da rubrica é demonstrada:

| Competência da rubrica | Notebook (executada, com saídas reais) | Seção do relatório |
|---|---|---|
| 1. Aplicações NLP com LLMs + Hugging Face | [`c01_modelos_llm.ipynb`](c01_modelos_llm.ipynb) | "Tarefas de PLN e Hugging Face" |
| 2. Prompt engineering + saídas controladas | [`c02_prompting.ipynb`](c02_prompting.ipynb) | "Engenharia de prompt e saída controlada" |
| 3. Embeddings semânticos + busca vetorial | [`c03_embeddings_busca.ipynb`](c03_embeddings_busca.ipynb) | "Embeddings, estratégia de busca e avaliação" |
| 4. Inferência local, remota ou privada | [`c04_inferencia_local_ou_remota.ipynb`](c04_inferencia_local_ou_remota.ipynb) | "Estratégia de inferência local ou remota" |
| 5. Pipeline RAG + segurança | [`c05_rag_pipeline.ipynb`](c05_rag_pipeline.ipynb) | "O pipeline RAG" + "Riscos de segurança" |
| Além da rubrica: detecção de antinomias | [`c06_antinomias.ipynb`](c06_antinomias.ipynb) | "Detecção de antinomias" |
| Além da rubrica: a lei como dado | [`c07_lei_como_dado.ipynb`](c07_lei_como_dado.ipynb) | "Análise Direito como Dado" |

- **Código completo:** pacote [`direito_dados/`](direito_dados/) (com 116 testes — `make test`)
  + as 7 notebooks acima, todas executadas com saídas embutidas (podem ser avaliadas sem rodar nada).
- **Pipeline RAG + este README** com instalação, preparação dos dados, indexação e consultas.
- **Relatório técnico (PDF):**
  [`report/anderson_correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf`](report/anderson_correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf)

## O corpus

O recorte é o conjunto de normas federais que estrutura o direito penal brasileiro — na
doutrina, um **microssistema**: um conjunto de leis que gravitam em torno de um código e
formam um subsistema coeso do ordenamento. Como legislar sobre direito penal é competência
privativa da União (CF, art. 22, I), o recorte federal é **completo por definição**, não
uma amostra. São 9 normas, **2.310 artigos** (2.248 em vigor, 62 revogados), obtidas dos
textos consolidados oficiais do Planalto:

- [Constituição da República Federativa do Brasil de 1988](https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm) — direitos e garantias, competência penal
- [Código Penal — Decreto-Lei nº 2.848/1940](https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm)
- [Código de Processo Penal — Decreto-Lei nº 3.689/1941](https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm)
- [Lei de Execução Penal — Lei nº 7.210/1984](https://www.planalto.gov.br/ccivil_03/leis/l7210compilado.htm)
- [Lei de Drogas — Lei nº 11.343/2006](https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11343.htm)
- [Lei Maria da Penha — Lei nº 11.340/2006](https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm)
- [Lei dos Crimes Hediondos — Lei nº 8.072/1990](https://www.planalto.gov.br/ccivil_03/leis/l8072.htm)
- [Lei das Contravenções Penais — Decreto-Lei nº 3.688/1941](https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm)
- [Lei de Introdução às Normas do Direito Brasileiro (LINDB) — Decreto-Lei nº 4.657/1942](https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm) — define os próprios critérios de resolução de conflitos entre normas

Um snapshot processado acompanha o repositório em `data/raw/` (textos de domínio público),
então nada precisa ser baixado para usar o projeto. Para rebaixar do Planalto: `make data`.

## Como funciona

```text
Textos consolidados do Planalto
   → Corpus     cada artigo com hierarquia normativa e situação de vigência,
                extraídas das anotações oficiais ("Redação dada...", "Revogado...")
   → Grafo      normas e artigos viram nós; emendas, revogações e conflitos
                candidatos viram arestas com proveniência
   → Busca      busca semântica (embeddings em português) combinada com busca
                por palavras-chave (BM25); normas revogadas excluídas por padrão
   → Resposta   o modelo local gera resposta em JSON com citações; cada citação
                é verificada contra o corpus; sem base suficiente, o sistema se abstém
   → Análises   linha do tempo de emendas, pirâmide de hierarquia, grafo da rede
   → Antinomias pares de normas similares são triados e um LLM avalia possível
                conflito, com o princípio de resolução aplicável (LINDB)
```

Estrutura do código (detalhes de chunking, embeddings e avaliação: notebook `c03` e
seções correspondentes do relatório):

```text
direito_dados/
  corpus/       # download + parsing + vigência + hierarquia (fonte única do texto legal)
  graph/        # grafo de normas (nós/arestas com proveniência e estado de verificação)
  adapters/     # interface de ingestão de fontes; implementado: Planalto
                #   (LexML e Câmara/Senado são trabalho futuro documentado no relatório)
  retrieval/    # chunking por artigo, embeddings (multilingual-e5), índice ChromaDB,
                #   BM25 + busca híbrida, avaliação de recuperação
  generation/   # cliente LLM (Ollama local), prompt citado, parsing validado, RAG
  analytics/    # linha do tempo, resumos, exportação e visualização do grafo
  conflicts/    # princípios LINDB, geração de candidatos, adjudicação, avaliação
scripts/        # demo.py, fetch_corpus.py, build_report.py
data/raw/       # snapshot das 9 normas (texto processado)
tests/          # 116 testes espelhando o pacote
```

## Propriedades de segurança

- **Vigência:** a busca exclui normas revogadas por padrão; a revogação é determinada em
  nível de artigo (a revogação de um parágrafo não revoga o artigo inteiro).
- **Citação verificada:** toda citação do modelo é conferida programaticamente contra o
  corpus; ids inexistentes são reportados como alucinados e nunca aceitos em silêncio.
- **Abstenção:** sem contexto recuperado, o sistema se recusa a responder — o modelo nem
  chega a ser chamado.
- **Privacidade:** a geração é local (Ollama); as perguntas não saem da máquina. Não há
  chaves, tokens ou segredos no repositório.
- Análise completa de riscos (injeção de prompt, vazamento de contexto) e controles:
  notebook `c05` e seção "Riscos de segurança" do relatório.

## Reprodução completa

```bash
make setup      # dependências Python (uv sync --all-extras)
make demo       # demonstração de ponta a ponta (independe do Ollama)
make models     # modelos locais: llama3.1:8b via Ollama + embeddings e5
make test       # 116 testes; os que exigem e5/Ollama pulam se indisponíveis
make notebooks  # re-executa as 7 notebooks (lento; exige Ollama ativo)
make report     # regenera o PDF a partir de report/relatorio.md
```

**Sem uv** (alternativa com pip):

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -r requirements.txt && pip install -e .
python scripts/demo.py
```

## Limitações

- A vigência cobre revogações e alterações **anotadas** nos textos consolidados do
  Planalto; *revogação tácita* e *inconstitucionalidade* exigem interpretação e estão fora
  do escopo determinístico (o detector de antinomias as aponta apenas como candidatos).
- Níveis normativos de mesma posição hierárquica (decreto-lei, lei ordinária, medida
  provisória) são tratados com o mesmo *rank* para fins de *lex superior*.
- A qualidade da resposta gerada é limitada pelo modelo local (8B parâmetros): a resposta
  pode citar um dispositivo existente porém semanticamente incorreto — limitação analisada
  em detalhe no relatório ("análise de falhas"), com os controles que a mitigam.
