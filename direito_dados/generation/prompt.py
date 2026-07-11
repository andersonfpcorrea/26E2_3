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
2. Se as provisões fornecidas respondem à pergunta, RESPONDA (defina \
"abstained": false) e liste em "citations" as tags dos dispositivos que você usou, \
usando o id exato de cada provisão (por exemplo "CP:art121", sem colchetes).
3. Abstenha-se ("abstained": true) SOMENTE quando as provisões não permitirem \
responder; nesse caso explique brevemente por quê.
4. Responda em português do Brasil.
5. Responda ESTRITAMENTE em JSON, sem texto fora do objeto JSON, com exatamente \
estas chaves: "answer" (string), "citations" (lista de ids como "CP:art121"), \
"hierarchy_notes" (string, pode ser vazia), "abstained" (booleano), \
"confidence" (número entre 0 e 1).

EXEMPLO de resposta correta quando o contexto contém [CP:art121] "Matar alguém: \
Pena - reclusão, de seis a vinte anos":
{"answer": "Matar alguém (homicídio) é punido com reclusão de 6 a 20 anos.", \
"citations": ["CP:art121"], "hierarchy_notes": "", "abstained": false, \
"confidence": 0.9}
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

    if results:
        ids = ", ".join(r.id for r in results)
        instruction = (
            f"\n\nIds disponíveis para citação: {ids}\n"
            'Em "citations", liste os ids exatos (ex.: "CP:art121") dos dispositivos '
            "acima que você usou na resposta. Se algum deles responder à pergunta, "
            'defina "abstained": false.'
        )
    else:
        instruction = ""

    return f"{context}\n\nPERGUNTA: {question}{instruction}"
