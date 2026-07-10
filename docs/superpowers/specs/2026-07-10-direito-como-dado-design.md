# O Direito como Dado — Design Spec

**Course:** Sistemas Cognitivos com Large Language Models (INFNET, 26E2_3)
**Author:** Anderson Felipe Paixão Corrêa
**Deliverable deadline:** 2026-07-13, 23:59 (attempt 1 of 2)
**Spec date:** 2026-07-10
**Status:** Approved for planning

---

## 1. One-line summary

An exploratory *"law as data"* system over the Brazilian criminal-law microsystem: a hierarchy-aware, citation-faithful RAG that lets a citizen **talk to the law** (grounded, cited answers — explicitly **not** legal advice), plus an analytics/visualization layer that makes the **structure, growth, and contradictions** of the corpus concrete and explorable.

## 2. Motivation and framing

Brazilian law is vast, layered, and self-amending to the point that even the question "which norm governs here, and is it still in force?" is hard for a citizen to answer. The project's civic goal is **democratizing understanding of the law's complexity** — not adjudicating anyone's legal situation.

This framing is deliberate and load-bearing:

- **Not a legal-advice / self-evaluation tool.** The system never concludes "you are/aren't breaking the law." It *finds, grounds, cites, and explains* relevant norms, surfaces *candidate* conflicts for human review, and abstains when unsure. This sidesteps unauthorized-practice-of-law liability and converts fuzzy questions ("is this good advice?") into measurable ones ("how many amendments? how many candidate conflicts? how fast is the corpus growing? what is the hallucinated-citation rate?").
- **Genre:** computational legal studies / legal informatics + applied NLP for Brazilian Portuguese (an under-resourced setting for legal LLM work).

### 2.1 Path to a publishable paper

The graded deliverable is the seed; the paper is the north star the professor helps grow. The publishable contribution is a **mixed systems + empirical** result:

1. **Hierarchy-aware RAG** — every chunk carries metadata (norm, article, hierarchy level, vigência status/date), and retrieval + generation reason about the norm hierarchy.
2. **Antinomy-candidate detector** with principle-based resolution (*lex superior / specialis / posterior*), evaluated by precision/recall on an expert-verified gold set.
3. **Faithfulness & safe-abstention evaluation** for citizen legal QA in Portuguese (hallucinated-citation rate, grounding, RAG-vs-no-RAG, local-vs-cloud).
4. **Empirical "law as data" analysis** — growth, structure, and authorship/trend patterns of the corpus.

Candidate venues (future): PROPOR / STIL (PT NLP), or legal-informatics / computational-social-science tracks.

## 3. Scope

### 3.1 Domain: the criminal-law microsystem (federal-exclusive)

Criminal legislative competence is constitutionally exclusive to the União (CF art. 22, I). Therefore scoping to **federal** law is *complete*, not truncated — state/municipal law is out of scope by law, not by convenience.

**Corpus (Planalto consolidated texts — all carry inline vigência annotations):**

- Constituição Federal (Título II — direitos e garantias fundamentais, esp. art. 5; penal-competence articles)
- Código Penal (Decreto-Lei 2.848/1940) — Parte Geral + Parte Especial
- Código de Processo Penal (Decreto-Lei 3.689/1941)
- Lei de Execução Penal (7.210/1984)
- Lei de Drogas (11.343/2006)
- Lei Maria da Penha (11.340/2006)
- Lei dos Crimes Hediondos (8.072/1990)
- Lei das Contravenções Penais (Decreto-Lei 3.688/1941)
- LINDB (Decreto-Lei 4.657/1942) — encodes the antinomy-resolution rules themselves

**External metadata catalog (for corpus-wide analytics):** LexML (federal-norm URNs, dates, types); Câmara/Senado open data (proposição authors/parties/dates).

**Jurisprudence / friction cases:** a small curated set (3–5), authored/verified by hand.

### 3.2 What is explicitly out of scope

- State and municipal law (excluded by constitutional competence for the criminal domain).
- Any output framed as legal advice or a determination of a user's legal status.
- Automated large-scale case-outcome mining (future work; only a small curated gallery now).
- Real-time cloud hosting of an open model (architected and justified in the report, not provisioned).
- Full-federal-corpus ingestion (future work; the honest blocker is *vigência* correctness at scale — see 3.3).

### 3.3 The vigência (validity) reality — why bounded scope is a feature

For the major codes, Planalto's consolidated *redação vigente* annotates each changed article: `(Redação dada pela Lei nº X, de ANO)`, `(Revogado pela Lei nº ...)`. We **parse these into metadata** and tag each chunk as in-force / revoked / amended, with dates. At microsystem scale this makes metadata-driven vigência tractable.

Two residual cases cannot be pre-computed from publish dates and are *interpretive*:

- **Revogação tácita** — a newer norm silently contradicting an older one (LINDB art. 2º, §1º); no annotation exists.
- **Inconstitucionalidade** — STF striking a norm down; lives in jurisprudence, not statute metadata.

Detecting/surfacing these residuals (as *candidates*, not verdicts) is precisely the novel contribution. On ~9 documents the candidate space is bounded and an expert gold set is buildable; at full-federal scale it is combinatorial and unlabelable — the honest reason to stay scoped.

## 4. Architecture

Two layers bridged by the antinomy detector.

- **Layer A — Talk to the Law:** grounded, cited RAG over full text.
- **Layer B — Law as Data:** analytics + visualization over metadata.
- **Bridge:** a conflict found in A is contextualized in B (when, by which amending laws, which era) and illustrated by the friction gallery.

### 4.1 Pipeline (Layer A)

1. **Ingestion** — fetch consolidated texts → parse into article-level units → tag hierarchy level + vigência status/date from inline annotations.
2. **Indexing** — chunk by article/provision → Portuguese embeddings (BERTimbau-based sentence-transformer or multilingual-e5) → vector store (ChromaDB or FAISS) with metadata.
3. **Retrieval** — hybrid (BM25 + dense) top-k with hierarchy-aware re-ranking; revoked chunks filtered/flagged.
4. **Generation** — augmented prompt with retrieved cited provisions → local model (primary) / cloud (baseline) → structured output (answer + citations + hierarchy notes + confidence/abstention flag) → parse/validate.
5. **Conflict module** — generate candidate antinomy pairs → LLM adjudication by resolution principles → surface with citations.
6. **Evaluation harness** — gold QA + gold antinomias → metrics (Section 5).

### 4.2 Inference strategy (rubric point 4)

- **Primary:** local/private model (Ollama or GPT4All, open weights, fully offline) — the "democratize + no data leaves your machine" path; strongest answer to the privacy of criminal-law queries.
- **Baseline:** OpenAI cloud call for a quality comparison (the rubric rewards comparison).
- **Architected, not built:** self-hosted open weights in a private cloud (own GPU VM running vLLM/Ollama in a VPC, no third-party logging, Brazil data residency for LGPD) — the production answer, written up as report deployment section + paper future work. Not provisioned (reproducibility + scope).

### 4.3 Module boundaries (deep modules, single source of truth)

- `corpus/` — owns fetch + parse + vigência + hierarchy metadata; sole owner of raw text.
- `retrieval/`, `generation/`, `conflicts/`, `analytics/` — separate deep modules with clean interfaces.
- Ingestion is corpus-agnostic, so scaling to more law is *data, not redesign*.

## 5. Evaluation methodology

### 5.1 Gold sets (small, expert-verified, authored by us)

- **Gold QA (~40 questions)** — each with reference answer + grounding article(s); includes out-of-scope/unanswerable items to test abstention.
- **Gold antinomias (~15)** — verified candidate conflicts from legal literature / known súmula histories.

### 5.2 Metrics

- **Hallucinated-citation rate** — every cited article must exist and say what the answer claims (programmatic check against the index). Headline safety number.
- **Retrieval quality** — top-k hit rate / MRR on gold QA; dense vs hybrid (BM25+dense).
- **RAG vs no-RAG** — hallucination reduction with grounding.
- **Local vs cloud** — privacy / quality / cost / latency table.
- **Antinomy detector** — precision / recall vs gold antinomias.
- **Abstention** — correct refusal rate on out-of-scope questions.
- **Hallucination-of-validity** — rate of citing revoked provisions as current, before/after vigência filtering.

### 5.3 Security analysis (rubric point 5)

- Prompt-injection resistance (adversarial documents/queries).
- Context / system-prompt leakage.
- Secret hygiene (env vars; nothing in repo).
- Validity-hallucination test (5.2).
- **Controls proposed:** citation-verification layer, vigência filtering, abstention thresholds, injection sanitization, output-schema validation.

## 6. Layer B — Law as Data

### 6.1 Free-from-parse analytics (no new dataset)

The same annotation parse used for vigência yields the **mutation timeline** of the microsystem: how each code grew, which laws touched which articles, in which decade.

### 6.2 Catalog analytics (external LexML / Câmara — ambitious tier)

- Corpus-wide legislative-**growth curve** (criminal-domain federal norms per year / cumulative).
- **Authorship / party / field trends** where data supports it. Honest limitation: party attribution is spotty for the decreto-lei era (e.g., the 1940 Código Penal was a Vargas decree — no party); coverage is reported, not glossed.

### 6.3 Visualization

- **Norm-hierarchy pyramid** populated with the corpus.
- **Microsystem network graph** — nodes = norms/articles; edges = amends / revokes / references / candidate-conflicts — built from extracted metadata + detector output. Visual centerpiece.

### 6.4 Friction gallery

3–5 curated, documented instances of interpretive friction (divergent rulings later unified by súmula; applied-then-struck provisions) tied to specific detected conflicts. Qualitative evidence that the complexity has real consequences. Automated mining = future work.

## 7. Deliverables

Per the rubric, three artifacts:

1. **Complete application code** — notebooks + supporting modules.
2. **RAG pipeline + README.md** — install deps, prepare documents, index the base, run queries.
3. **Technical report (PDF)** — problem, corpus, LLM justification, models/tools, NLP tasks, prompting strategy + tested versions + evaluation, structured-output/parsing, embeddings + search strategy, query/retrieval examples, inference strategy + privacy/cost/latency justification, RAG description, chunking, vector store, answers with/without context, failure analysis, security risks + controls, reproduction instructions, limitations, future work.
   - Filename: `correa_sistemas-cognitivos-linguagem-natural_aplicacoes-llms.pdf`

### 7.1 File structure

- `c01_modelos_llm.ipynb` — HF pretrained models, tokenization, encoder-vs-decoder, a legal NLP task + model comparison.
- `c02_prompting.ipynb` — ≥3 prompting techniques, structured JSON output, parsing/validation, prompt iteration with explicit quality criteria.
- `c03_embeddings_busca.ipynb` — Portuguese embeddings, vector store, dense-vs-hybrid retrieval, metadata filtering, retrieval eval.
- `c04_inferencia_local_ou_remota.ipynb` — local vs cloud + private-cloud architecture write-up.
- `c05_rag_pipeline.ipynb` — full grounded/cited RAG with hierarchy rerank + vigência filter + abstention; hallucination + security analysis.
- `c06_antinomias.ipynb` — conflict detection + principle-based resolution + precision/recall + friction gallery.
- `c07_lei_como_dado.ipynb` — Layer B analytics + visualizations.
- Supporting: ingestion/modules package, `requirements.txt`, `README.md`, `data/` (raw / processed / gold).

## 8. Rubric coverage map

- **Point 1 (NLP with LLMs + HF):** c01 — pretrained models, tokenization, encoder-vs-decoder, task + model comparison, tied to the legal corpus.
- **Point 2 (Prompt engineering + controlled output):** c02 — ≥3 techniques, JSON schema output, parsing/validation, iteration.
- **Point 3 (Embeddings + vector search):** c03 — Portuguese embeddings, ChromaDB/FAISS, dense-vs-hybrid, retrieval success/failure analysis.
- **Point 4 (Local / remote / private inference):** c04 — local-primary + cloud baseline comparison; privacy/cost/latency/control; private-cloud architecture.
- **Point 5 (RAG + grounded answer + security):** c05/c06 — full pipeline, chunking analysis, hallucination reduction, prompt-injection + leakage risks + controls, reproducibility, no secrets.

## 9. Execution plan (graceful degradation)

Build in strict priority order so that at *any* cutoff a complete, rubric-passing project exists; ambitious enrichment layers on top.

- **Day 1 (graded core):** corpus module + metadata; embeddings + index; baseline RAG (c01, c03, c05 skeleton). Parallelizable: ingest 9 docs ‖ pull external catalog ‖ draft gold sets.
- **Day 2 (grade-critical rigor):** prompting + structured output + eval harness + local/cloud comparison + antinomy detector (c02, c04, c06).
- **Day 3 (ambitious enrichment + report):** Layer B analytics + catalog + visualizations + friction gallery (c07) + write the PDF. If time slips, degrades cleanly to "future work" with the grade already secured.

## 10. Risks and mitigations

- **Local model weak on PT legal reasoning** → cloud baseline contextualizes numbers; abstention protects faithfulness.
- **Ambitious scope vs deadline** → strict priority order + parallelization; Layer B is degradable.
- **External catalog data quality (authorship/party gaps)** → report coverage honestly; do not over-claim.
- **Vigência edge cases (tácita/inconstitucionalidade)** → surfaced as candidates for human review, never as verdicts.
- **Over-claiming conflict detection** → framed as candidate detection with precision/recall, not an oracle.

## 11. Open questions for planning

- Exact local model (Ollama model id vs GPT4All build) and exact PT embedding model — pin during planning.
- Vector store choice (ChromaDB vs FAISS) — pin during planning.
- Whether c06/c07 stay separate notebooks or merge if time is tight.
