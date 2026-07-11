# O Direito como Dado — RAG e Análise do Microssistema Penal Federal

Sistema exploratório de **"direito como dado"** sobre o microssistema penal federal
brasileiro: um RAG *hierarquia-* e *vigência-aware* que permite **conversar com a lei**
(respostas fundamentadas e citadas — explicitamente **não** aconselhamento jurídico), um
**detector de antinomias** (conflitos candidatos entre normas) e uma camada de **análise e
visualização** que torna a estrutura, o crescimento e as contradições do corpus exploráveis.

> **Aviso.** Esta é uma ferramenta de *pesquisa e compreensão* da legislação. Ela **não**
> constitui consulta, parecer ou aconselhamento jurídico, e nunca conclui sobre a situação
> legal de ninguém. Conflitos e resoluções são apresentados como **candidatos para revisão
> humana**, jamais como veredito.

**Disciplina:** Sistemas Cognitivos com Large Language Models (INFNET, 26E2_3)
**Autor:** Anderson Felipe Paixão Corrêa

---

## O que faz

Pipeline completo, do texto bruto à resposta fundamentada e à análise:

```
Textos consolidados do Planalto
  → Corpus        (artigos + hierarquia + vigência, a partir das anotações inline)
  → Norm-graph    (arestas amends/revokes/conflito + proveniência)
  → Retrieval     (embeddings PT + ChromaDB, exclui normas revogadas; denso + híbrido)
  → RAG           (resposta citada + verificação de citação alucinada + abstenção)
  → Analytics     (linha do tempo de emendas, pirâmide de hierarquia, grafo de rede)
  → Conflitos     (detector de antinomias: candidatos → princípios LINDB → precisão/revocação)
```

Corpus (9 normas do microssistema penal, competência federal exclusiva — CF art. 22, I):
CF, Código Penal, CPP, LEP, Lei de Drogas (11.343), Maria da Penha (11.340), Crimes
Hediondos (8.072), Contravenções Penais (DL 3.688) e LINDB.

**Números do corpus (reproduzíveis a partir do snapshot em `data/raw/`):**
2.310 artigos · 2.248 em vigor · 62 revogados · grafo com 2.381 nós e 4.453 arestas de emenda.

## Instalação

```bash
python3 -m venv .venv          # Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt
```

Para geração local (opcional, para o RAG e o detector de antinomias) instale o
[Ollama](https://ollama.com) e baixe um modelo:

```bash
ollama serve                   # ou abra o app do Ollama
ollama pull llama3.1           # ~4.7GB
```

## Preparar os dados

O corpus processado já acompanha o repositório em `data/raw/` (textos de domínio público).
Para rebaixá-lo do Planalto (opcional):

```bash
PYTHONPATH=. python scripts/fetch_corpus.py
```

## Uso

```python
from direito_dados.corpus import load_corpus, NORMS
from direito_dados.retrieval.chunks import chunk_corpus
from direito_dados.retrieval.embedder import E5Embedder
from direito_dados.retrieval.index import VectorIndex

corpus = load_corpus("data/raw")                 # 9 normas
chunks = chunk_corpus(corpus)
embedder = E5Embedder()                          # intfloat/multilingual-e5-base
index = VectorIndex.build(chunks, embedder)

# Recuperação (normas revogadas são excluídas por padrão)
for r in index.query("qual a pena para quem mata alguém?", embedder, k=5):
    print(r.citation, round(r.score, 3))
```

RAG com geração local (requer Ollama ativo):

```python
from direito_dados.generation.llm import OllamaClient
from direito_dados.generation.rag import answer_question

valid = {c.id for c in chunks}
ans = answer_question("qual a pena para quem mata alguém?", index, embedder,
                      OllamaClient(model="llama3.1"), k=5, valid_ids=valid)
print(ans.answer)
print("citações:", ans.citations, "| alucinadas:", ans.hallucinated_citations)
```

Análise "direito como dado":

```python
from direito_dados.graph import build_graph
from direito_dados.analytics.timeline import amendments_by_decade

g = build_graph(corpus)
print(amendments_by_decade(g))   # emendas por década — vê-se a reforma de 1984 e a onda de 2019–2020
```

Detecção de antinomias (candidatos, requer Ollama):

```python
from direito_dados.conflicts.candidates import generate_candidates
from direito_dados.conflicts.detect import detect_conflicts

cands = generate_candidates(chunks, index, embedder, k=3, threshold=0.85)
conflicts = detect_conflicts(cands[:20], {c.id: c for c in chunks}, corpus,
                             OllamaClient(model="llama3.1"), min_confidence=0.5)
for c in conflicts:
    print(c.a, "×", c.b, "→", c.principle)
```

## Testes

```bash
python -m pytest -q            # ~114 testes; testes com o modelo real e o Ollama
                              # rodam quando as dependências/serviço estão disponíveis,
                              # e são pulados (skip) caso contrário.
```

## Estrutura

```
direito_dados/
  corpus/       # fetch + parse + vigência + hierarquia (fonte única do texto)
  graph/        # norm-graph agnóstico de domínio (nós/arestas + proveniência)
  adapters/     # SourceAdapter — a costura "plugue qualquer lei"
  retrieval/    # chunking, embeddings (e5), índice ChromaDB, BM25/híbrido, avaliação
  generation/   # LLMClient (Fake/Ollama), prompt citado, parsing, pipeline RAG
  analytics/    # linha do tempo, resumos, exportação de rede, gráficos
  conflicts/    # princípios LINDB, candidatos, adjudicação LLM, avaliação
scripts/        # fetch_corpus.py
data/raw/       # snapshot das 9 normas (texto processado)
tests/          # espelham direito_dados/
```

## Propriedades de segurança

- **Vigência:** normas revogadas são excluídas da recuperação por padrão; a revogação é
  determinada em nível de artigo (uma revogação de parágrafo não revoga o artigo inteiro).
- **Citação fundamentada:** toda citação emitida pelo modelo é verificada contra o corpus;
  citações inexistentes são sinalizadas como **alucinadas** e nunca aceitas silenciosamente.
- **Abstenção:** sem base recuperada, o sistema se abstém em vez de fabricar resposta.
- **Sem segredos no repositório;** a geração local mantém as consultas na sua máquina.

## Limitações

- Vigência cobre revogação/alteração anotadas no Planalto; *revogação tácita* e
  *inconstitucionalidade* são interpretativas e ficam fora do escopo determinístico.
- Níveis de hierarquia que compartilham posição (decreto-lei, lei ordinária, medida
  provisória) são tratados com o mesmo *rank* para *lex superior*.
- A qualidade das respostas depende do modelo local; um LLM fraco pode se abster com
  frequência (motivo para comparar com um baseline em nuvem no relatório).
