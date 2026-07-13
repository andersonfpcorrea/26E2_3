"""ChromaDB-backed vector index with vigência/domain metadata filtering.

Default retrieval EXCLUDES revoked provisions — the retrieval-level form of the
project's vigência safety property (never surface repealed law as an answer).
"""

from dataclasses import dataclass

from direito_dados.retrieval.chunks import Chunk
from direito_dados.retrieval.embedder import Embedder

REVOGADO_STATUS = "revogado"


@dataclass(frozen=True)
class Result:
    id: str
    text: str
    citation: str
    score: float
    metadata: dict


class VectorIndex:
    def __init__(self, collection):
        self._collection = collection

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder, persist_dir: str | None = None):
        import chromadb

        client = chromadb.PersistentClient(path=persist_dir) if persist_dir else chromadb.EphemeralClient()
        # Fresh collection each build (idempotent for tests).
        try:
            client.delete_collection("norms")
        except Exception:
            pass
        collection = client.create_collection("norms", metadata={"hnsw:space": "cosine"})
        if chunks:
            collection.add(
                ids=[c.id for c in chunks],
                embeddings=embedder.embed_passages([c.embed_text or c.text for c in chunks]),
                documents=[c.text for c in chunks],
                metadatas=[c.metadata for c in chunks],
            )
        return cls(collection)

    @classmethod
    def open_or_build(cls, chunks: list[Chunk], embedder: Embedder, persist_dir: str):
        """Reuse a persisted index when it matches `chunks`; (re)build otherwise.

        Embedding the corpus is the expensive step (minutes on CPU), but the
        result is deterministic for a given corpus snapshot — so it is paid
        once and persisted. The index is reused only when the stored ids match
        the expected chunk ids exactly; any corpus change triggers a rebuild.
        """
        existing = _persisted_collection(chunks, persist_dir)
        if existing is not None:
            return cls(existing)
        return cls.build(chunks, embedder, persist_dir=persist_dir)

    def query(self, text: str, embedder: Embedder, k: int = 5,
              exclude_revoked: bool = True, domain: str | None = None) -> list[Result]:
        conditions = []
        if exclude_revoked:
            conditions.append({"status": {"$ne": REVOGADO_STATUS}})
        if domain is not None:
            conditions.append({"domain": {"$eq": domain}})
        where = None if not conditions else (conditions[0] if len(conditions) == 1 else {"$and": conditions})

        res = self._collection.query(
            query_embeddings=[embedder.embed_query(text)],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[Result] = []
        ids = res["ids"][0]
        for i, cid in enumerate(ids):
            meta = res["metadatas"][0][i]
            dist = res["distances"][0][i]
            out.append(Result(
                id=cid, text=res["documents"][0][i], citation=meta.get("citation", cid),
                score=1.0 - dist, metadata=meta,
            ))
        return out


def persisted_matches(chunks: list[Chunk], persist_dir: str) -> bool:
    """True when `persist_dir` holds an index for exactly these chunks."""
    return _persisted_collection(chunks, persist_dir) is not None


def _persisted_collection(chunks: list[Chunk], persist_dir: str):
    import chromadb

    try:
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_collection("norms")
        if collection.count() == len(chunks):
            stored = set(collection.get(include=[])["ids"])
            if stored == {c.id for c in chunks}:
                return collection
    except Exception:
        pass
    return None
