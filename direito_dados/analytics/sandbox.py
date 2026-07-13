"""Model-generated aggregation scripts, executed over the data only.

When an aggregate question falls outside the preset tools, the local model
writes a small Python script against a FLATTENED, read-only dataset of the
corpus and the script runs in a restricted subprocess: no imports, a safe
builtin whitelist, a hard timeout, and nothing exposed but the data rows.
The generated code is returned alongside the result so the user can audit it.

Threat model note: this is a LOCAL, single-user tool — the question author is
the machine owner, so the guard's purpose is preventing accidents (a flaky
model touching files) and keeping results auditable, not stopping a hostile
attacker. For any public deployment this feature must stay disabled or gain
real OS-level isolation.
"""

import json
import subprocess
import sys
from dataclasses import dataclass

from direito_dados.analytics.penalties import extract_penalties
from direito_dados.corpus.loader import Corpus
from direito_dados.generation.llm import LLMClient
from direito_dados.generation.parse import extract_json_object
from direito_dados.graph.models import EdgeKind, NormGraph

_TIMEOUT_S = 10

# Executed in a subprocess: reads {dataset, script} JSON on stdin, runs the
# script with restricted builtins over `artigos`, prints `resultado` as JSON.
_HARNESS = r"""
import json, sys
payload = json.load(sys.stdin)
artigos = payload["dataset"]
from collections import Counter
SAFE = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
        for n in ("len","max","min","sorted","sum","filter","map","set","list","dict",
                   "str","int","float","round","any","all","enumerate","range","abs",
                   "zip","reversed","tuple","bool")}
scope = {"__builtins__": SAFE, "artigos": artigos, "Counter": Counter}
exec(payload["script"], scope)
if "resultado" not in scope:
    print(json.dumps({"erro": "o script executou mas não atribuiu a variável 'resultado'"}))
else:
    print(json.dumps({"resultado": scope["resultado"]}, ensure_ascii=False, default=str))
"""

_SCRIPT_SYSTEM = (
    "Você escreve UM script Python curto para responder uma pergunta agregada "
    "sobre a legislação penal brasileira. O script recebe a lista `artigos` "
    "(um dict por artigo) e DEVE atribuir a resposta à variável `resultado` "
    "(string, número, dict ou lista pequena — inclua a citação dos artigos "
    "relevantes). Sem imports (Counter já está disponível), sem input/output, "
    "sem acessar arquivos: apenas computação sobre `artigos`.\n\n"
    "Campos de cada artigo: norma (sigla), citacao (ex. 'CP art. 121'), "
    "rubrica (nome oficial do crime, pode ser vazio), status "
    "('vigente'/'alterado'/'revogado'), texto (texto integral), "
    "pena_min_meses e pena_max_meses (int ou null quando o artigo não comina "
    "pena), pena_trecho (trecho literal da pena), alteracoes (quantas emendas "
    "o artigo recebeu).\n\n"
    "Exemplo 1 — pergunta: 'qual artigo tem a maior pena?' → script:\n"
    "com_pena = [a for a in artigos if a['pena_max_meses']]\n"
    "top = max(com_pena, key=lambda a: a['pena_max_meses'])\n"
    "resultado = f\"{top['citacao']} — {top['pena_trecho']}\"\n\n"
    "Exemplo 2 — pergunta: 'quantos artigos mencionam arma?' → script "
    "(buscas de palavra usam o campo 'texto', em minúsculas):\n"
    "achados = [a for a in artigos if 'arma' in a['texto'].lower()]\n"
    "resultado = f\"{len(achados)} artigos; ex.: \" + ', '.join(a['citacao'] for a in achados[:5])\n\n"
    'Responda em JSON com a chave única "script", contendo CÓDIGO Python — nunca a resposta pronta.'
)

_SCRIPT_SCHEMA = {"type": "object", "properties": {"script": {"type": "string"}},
                  "required": ["script"]}


@dataclass
class ScriptResult:
    script: str
    output: str
    ok: bool
    error: str = ""


def build_dataset(corpus: Corpus, graph: NormGraph) -> list[dict]:
    """One flat dict per article — simple enough for a small model to query."""
    amend_counts: dict[str, int] = {}
    for e in graph.edges:
        if e.kind in (EdgeKind.AMENDS, EdgeKind.REVOKES):
            amend_counts[e.dst] = amend_counts.get(e.dst, 0) + 1
    rows = []
    for norm in corpus.norms:
        for art in norm.articles:
            pens = extract_penalties(art.text)
            worst = max(pens, key=lambda p: p.max_months) if pens else None
            rows.append({
                "norma": norm.id,
                "citacao": art.citation,
                "rubrica": art.rubrica,
                "status": art.status.value,
                "texto": art.text,
                "pena_min_meses": worst.min_months if worst else None,
                "pena_max_meses": worst.max_months if worst else None,
                "pena_trecho": worst.excerpt if worst else "",
                "alteracoes": amend_counts.get(f"{norm.id}:art{art.number}", 0),
            })
    return rows


def run_script(script: str, dataset: list[dict]) -> ScriptResult:
    """Execute a script over the dataset in a restricted subprocess."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _HARNESS],
            input=json.dumps({"dataset": dataset, "script": script}),
            capture_output=True, text=True, timeout=_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ScriptResult(script, "", False, f"tempo excedido ({_TIMEOUT_S}s)")
    if proc.returncode != 0:
        return ScriptResult(script, "", False, proc.stderr.strip().splitlines()[-1] if proc.stderr else "erro")
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return ScriptResult(script, "", False, "saída inválida do script")
    if "erro" in payload:
        return ScriptResult(script, "", False, payload["erro"])
    out = payload["resultado"]
    text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2)
    return ScriptResult(script, text, True)


def generate_and_run(question: str, dataset: list[dict], llm: LLMClient,
                     retries: int = 1) -> ScriptResult | None:
    """Ask the model for a script, run it; on failure, retry once with the error."""
    prompt = f"Pergunta: {question}"
    result = ScriptResult("", "", False, "o modelo não produziu um script")
    for _ in range(retries + 1):
        raw = llm.generate(prompt, system=_SCRIPT_SYSTEM, format=_SCRIPT_SCHEMA)
        data = extract_json_object(raw) or {}
        script = str(data.get("script", "")).strip()
        if not script:
            prompt = (f"Pergunta: {question}\n\nSua resposta anterior veio vazia. "
                      "Escreva um script Python que atribui a variável 'resultado'.")
            continue
        if "resultado" not in script:
            # The model answered with data instead of code — correct and retry.
            result = ScriptResult(script, "", False,
                                  "o script deve ser código Python que ATRIBUI a "
                                  "variável 'resultado' (não a resposta pronta)")
            prompt = (f"Pergunta: {question}\n\nSua resposta anterior não era um "
                      f"script válido: {result.error}. Escreva código Python.")
            continue
        result = run_script(script, dataset)
        if result.ok:
            return result
        prompt = (f"Pergunta: {question}\n\nSeu script anterior falhou com o erro: "
                  f"{result.error}\nScript anterior:\n{script}\nCorrija-o.")
    return result
