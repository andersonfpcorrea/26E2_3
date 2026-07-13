# Letra da Lei

Um sistema que permite **conversar com a legislação penal federal brasileira**, e mostra como
ela cresceu, o que está em vigor, o que foi revogado e onde duas normas podem se contradizer.

> **Aviso:** ferramenta de _pesquisa e compreensão_ da legislação. Não constitui consulta,
> parecer ou aconselhamento jurídico. Conflitos entre normas são apresentados como
> **candidatos para revisão**.

**Disciplina:** Sistemas Cognitivos com Large Language Models (INFNET, 26E2_3) ·

**Autor:** Anderson Corrêa

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

Toda citação que o modelo produz é conferida contra o corpus oficial: citações
inexistentes são sinalizadas como **alucinação** e descartadas; sem base recuperada, o sistema
não responde.

**2. Sabe o que ainda é lei — e o que deixou de ser.** Cada um dos 2.310 artigos carrega sua situação
(em vigor / alterado / revogado), extraída das anotações oficiais do Planalto, e a busca
**exclui normas revogadas**.

**3. Revela a estrutura e a história da lei.** As 4.453 emendas do corpus formam um grafo e
uma linha do tempo — os picos de 1984 (reforma da Parte Geral) e de 2019–2020 ("pacote
anticrime") aparecem nos dados — e um detector aponta **candidatos a antinomia** (normas
possivelmente conflitantes), classificados pelos critérios clássicos de resolução
(_lex superior, lex specialis, lex posterior_ — LINDB). Uma camada opcional (`make
attribution`) resolve, para cada norma externa, quem mudou a lei — projeto de origem e
autoria de registro do Congresso, via dados abertos do Senado e da Câmara.

## Comece com um comando

Requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) (gerenciador
Python; instala o próprio Python 3.13 se preciso). Opcional: [Ollama](https://ollama.com)
para a geração local de respostas.

```bash
make run       # instala o que faltar (verifica antes de baixar, pula o que já existe)
               # e abre a interface web com tudo funcionando
```

### Comandos individuais

```bash
make setup     # só as dependências Python (uv sync)
make demo      # demonstração no terminal: corpus, grafo, análises e busca citada
make models    # só os modelos locais (verifica e baixa apenas o que faltar)
make ask q="qual a pena para furto?"   # pergunta direta no terminal
```

O sistema usa **dois modelos**. O de _embeddings_
(busca semântica, ~440 MB) baixa automaticamente na primeira execução — a busca citada, o
filtro de vigência, as análises e o grafo funcionam só com ele. O de _geração_ (Llama 3.1
8B, ~4,9 GB) roda no [Ollama](https://ollama.com), um aplicativo separado, e serve apenas à
etapa final: redigir respostas em linguagem natural. **Nada é simulado** — todas as etapas
rodam o pipeline real; _mocks_ existem somente nos testes unitários.

Todos os comandos: `make help`. Alternativa sem uv no final deste arquivo.

## Entregáveis e mapa da avaliação

| Competência da rubrica                     | Notebook (executada, com saídas reais)                                         | Seção do relatório                            |
| ------------------------------------------ | ------------------------------------------------------------------------------ | --------------------------------------------- |
| 1. Aplicações NLP com LLMs + Hugging Face  | [`c01_modelos_llm.ipynb`](c01_modelos_llm.ipynb)                               | "Tarefas de PLN e Hugging Face"               |
| 2. Prompt engineering + saídas controladas | [`c02_prompting.ipynb`](c02_prompting.ipynb)                                   | "Engenharia de prompt e saída controlada"     |
| 3. Embeddings semânticos + busca vetorial  | [`c03_embeddings_busca.ipynb`](c03_embeddings_busca.ipynb)                     | "Embeddings, estratégia de busca e avaliação" |
| 4. Inferência local, remota ou privada     | [`c04_inferencia_local_ou_remota.ipynb`](c04_inferencia_local_ou_remota.ipynb) | "Estratégia de inferência local ou remota"    |
| 5. Pipeline RAG + segurança                | [`c05_rag_pipeline.ipynb`](c05_rag_pipeline.ipynb)                             | "O pipeline RAG" + "Riscos de segurança"      |
| Além da rubrica: detecção de antinomias    | [`c06_antinomias.ipynb`](c06_antinomias.ipynb)                                 | "Detecção de antinomias"                      |
| Além da rubrica: a lei como dado           | [`c07_lei_como_dado.ipynb`](c07_lei_como_dado.ipynb)                           | "Análise 'a lei como dado'"                   |

- **Código completo:** pacote [`direito_dados/`](direito_dados/) (com 169 testes — `make test`)
  - as 7 notebooks acima, todas executadas com saídas embutidas (podem ser avaliadas sem rodar nada).
- **Pipeline RAG + este README** com instalação, preparação dos dados, indexação e consultas.
- **Relatório técnico (PDF):**
  [`report/anderson_correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf`](report/anderson_correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf)

## O corpus

O recorte é um **microssistema**: um conjunto de leis que gravitam em torno de um código e
formam um subsistema coeso do ordenamento. São 9 normas, **2.310 artigos** (2.248 em vigor, 62 revogados), obtidas dos
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
tests/          # 169 testes espelhando o pacote
```

## Propriedades de segurança

- **Vigência:** a busca exclui artigos revogadas; a revogação de um parágrafo não revoga o artigo inteiro.
- **Citação verificada:** toda citação do modelo é conferida contra o
  corpus; ids inexistentes são reportados como alucinados.
- **Abstenção:** sem contexto recuperado o sistema não responde.
- **Privacidade:** a geração é local (Ollama). Não há chaves, tokens ou segredos no repositório.
- Análise completa de riscos (injeção de prompt, vazamento de contexto) e controles:
  notebook `c05` e seção "Riscos de segurança" do relatório.

## Reprodução completa

```bash
make setup      # dependências Python (uv sync --all-extras)
make demo       # demonstração de ponta a ponta (independe do Ollama)
make models     # modelos locais: llama3.1:8b via Ollama + embeddings e5
make test       # 169 testes
make notebooks  # executa os 7 notebooks
make report     # produz o PDF a partir de report/relatorio.md
```

**Sem uv** (alternativa com pip):

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -r requirements.txt && pip install -e .
python scripts/demo.py
```

## Interface web

`make run` abre uma interface local em Streamlit ("Letra da Lei") com seis abas: perguntas
à lei com citações verificadas — incluindo a verificação do **trecho de sustentação**
(*quote-then-answer*): o modelo é obrigado a copiar o excerto literal que embasa a resposta,
e o sistema confere se o excerto existe no dispositivo citado, alertando atribuições
incorretas —, a linha do tempo das emendas, o grafo normativo interativo,
os candidatos a antinomia, o painel de vigência e "Quem mudou a lei" (autoria de registro
por norma). Tudo funciona de imediato: o corpus e o dataset de autoria **já acompanham o
repositório**, e o `make run` verifica cada um e só reconstrói o que estiver ausente —
por isso `make attribution` (refazer a autoria direto das APIs do Congresso) e `make data`
(rebaixar o corpus do Planalto) normalmente nunca precisam ser executados; existem para
reprodutibilidade a partir da fonte. A interface é uma camada **além da rubrica** (os
entregáveis avaliados são as notebooks, o pacote e o relatório).

## Limitações

- A vigência cobre revogações e alterações **anotadas** nos textos consolidados do
  Planalto; _revogação tácita_ e _inconstitucionalidade_ exigem interpretação e estão fora
  do escopo determinístico (o detector de antinomias as aponta apenas como candidatos).
- Níveis normativos de mesma posição hierárquica (decreto-lei, lei ordinária, medida
  provisória) são tratados com o mesmo _rank_ para fins de _lex superior_.
- A qualidade da resposta gerada é limitada pelo modelo local (8B parâmetros): a resposta
  pode citar um dispositivo existente porém semanticamente incorreto — limitação analisada
  em detalhe no relatório ("análise de falhas"), com os controles que a mitigam.
