"""Turn a parsed Corpus into retrievable chunks (one per article) with metadata."""

from dataclasses import dataclass

from direito_dados.corpus.loader import Corpus


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict


def chunk_corpus(corpus: Corpus) -> list[Chunk]:
    chunks: list[Chunk] = []
    for norm in corpus.norms:
        for art in norm.articles:
            if not art.text.strip():
                continue
            chunks.append(Chunk(
                id=f"{norm.id}:art{art.number}",
                text=art.text,
                metadata={
                    "norm_id": norm.id,
                    "article": art.number,
                    "urn": norm.urn,
                    "domain": norm.domain,
                    "hierarchy_level": norm.level.value,
                    "status": art.status.value,
                    "citation": art.citation,
                },
            ))
    return chunks
