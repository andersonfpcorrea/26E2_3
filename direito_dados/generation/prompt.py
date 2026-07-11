"""Cited-context prompt builder for the grounded RAG pipeline.

Renders the retrieved, in-force provisions as an explicit `[id]`-tagged context
block so the model can cite exactly what it used, and packages the guardrails
(answer only from context, cite by id, abstain when insufficient, respond as
strict JSON) into a fixed system prompt.
"""

from direito_dados.retrieval.index import Result

SYSTEM_PROMPT = """Você é um assistente que explica Direito Penal brasileiro a partir de \
trechos de normas fornecidos abaixo. Isto é uma explicação informativa, NÃO é \
aconselhamento jurídico.

Regras obrigatórias:
1. Responda SOMENTE com base nas PROVISÕES fornecidas no contexto. Não use \
conhecimento externo nem invente dispositivos.
2. Sempre que usar uma provisão, cite-a pela tag exata entre colchetes, \
por exemplo [CP:art121].
3. Se as provisões fornecidas não permitirem responder à pergunta, defina \
"abstained": true e explique brevemente por que não há base suficiente.
4. Responda em português do Brasil.
5. Responda ESTRITAMENTE em JSON, sem texto fora do objeto JSON, com exatamente \
estas chaves:
   - "answer": string com a resposta (ou a justificativa da abstenção)
   - "citations": lista das tags "[id]" das provisões efetivamente citadas
   - "hierarchy_notes": string com observações sobre hierarquia normativa, \
se relevante (pode ser vazia)
   - "abstained": booleano indicando se você se absteve de responder
   - "confidence": número entre 0 e 1 indicando sua confiança na resposta
"""


def build_user_prompt(question: str, results: list[Result]) -> str:
    """Render the retrieved provisions and the question as the user turn.

    Each provision is rendered as ``[id] (citation, situação: status)`` followed
    by its text. When `results` is empty, the prompt instructs the model to
    abstain instead of answering from outside knowledge.
    """
    if not results:
        context = (
            "PROVISÕES: nenhuma provisão relevante foi encontrada na base de "
            "normas para esta pergunta. Não há contexto para responder.\n"
            'Responda com "abstained": true, explicando que não há base '
            "normativa recuperada."
        )
    else:
        blocks = []
        for r in results:
            status = r.metadata.get("status", "?")
            blocks.append(f"[{r.id}] ({r.citation}, situação: {status})\n{r.text}")
        context = "PROVISÕES:\n\n" + "\n\n".join(blocks)

    return f"{context}\n\nPERGUNTA: {question}"
