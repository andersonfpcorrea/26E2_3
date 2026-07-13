"""Turn a parsed Corpus into retrievable chunks (one per article) with metadata."""

from dataclasses import dataclass

from direito_dados.corpus.loader import Corpus


_EMBED_TEXT_CAP = 300


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict
    embed_text: str = ""


def chunk_corpus(corpus: Corpus) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen_ids: set[str] = set()
    for norm in corpus.norms:
        for art in norm.articles:
            if not art.text.strip():
                continue
            chunk_id = f"{norm.id}:art{art.number}"
            # Annexed documents on the same Planalto page (e.g. the ADCT after
            # the constitutional body) restart article numbering; the first
            # occurrence — the consolidated main body — is the citable one.
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            # The rubrica (official crime name) is the strongest retrieval
            # signal for name-based queries, so it leads the embedded text.
            prefix = f"{art.rubrica}. " if art.rubrica else ""
            embed_text = f"{prefix}{art.caput}. {art.text}"[:_EMBED_TEXT_CAP]
            chunks.append(Chunk(
                id=f"{norm.id}:art{art.number}",
                text=art.text,
                embed_text=embed_text,
                metadata={
                    "norm_id": norm.id,
                    "article": art.number,
                    "urn": norm.urn,
                    "domain": norm.domain,
                    "hierarchy_level": norm.level.value,
                    "status": art.status.value,
                    "citation": art.citation,
                    "rubrica": art.rubrica,
                },
            ))
    return chunks
