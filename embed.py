"""
Stage 3 — Embedding & Vector Store
The Unofficial Guide RAG Pipeline

Embeds chunks with sentence-transformers/all-MiniLM-L6-v2 producing
L2-normalised 384-dim dense vectors, stored in a ChromaDB-backed vector store.
"""

import logging
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("embed")

# ─── Constants ────────────────────────────────────────────────────────────────

N_COMPONENTS = 384       # all-MiniLM-L6-v2 output dimensions
DISTANCE_THRESHOLD = 0.6 # Quality gate from planning.md: scores > 0.6 = weak match
DB_TABLE = "vectors"


# ─── Vector Store ─────────────────────────────────────────────────────────────

class VectorStore:
    """
    Lightweight ChromaDB-backed vector store.

    Schema mirrors the mandatory metadata spec from planning.md:
        source_document, chunk_index, source_type, raw_text_payload

    Persists between sessions. Supports add() and query().
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        path_obj = Path(db_path)
        self._collection_name = path_obj.stem or DB_TABLE
        persist_dir = path_obj.parent / "chroma"
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore initialised at '%s' (collection='%s')",
            persist_dir,
            self._collection_name,
        )

    def count(self) -> int:
        return self._collection.count()

    def add(self, ids: list[str], vectors: np.ndarray, metadatas: list[dict]):
        """Insert vectors with mandatory metadata fields."""
        assert len(ids) == len(vectors) == len(metadatas), \
            "ids, vectors, metadatas must have equal length"

        embeddings = []
        documents = []
        payload_metas = []
        for vid, vec, meta in zip(ids, vectors, metadatas):
            # Enforce mandatory metadata fields
            assert "source_document" in meta and meta["source_document"], \
                f"Missing 'source_document' in metadata for id={vid}"
            assert "chunk_index" in meta, \
                f"Missing 'chunk_index' in metadata for id={vid}"
            assert "raw_text_payload" in meta and meta["raw_text_payload"], \
                f"Missing 'raw_text_payload' in metadata for id={vid}"

            embeddings.append(np.asarray(vec, dtype=np.float32).tolist())
            documents.append(meta["raw_text_payload"])
            payload_metas.append({
                "source_document": meta["source_document"],
                "chunk_index": int(meta["chunk_index"]),
                "source_type": meta.get("source_type", "unknown"),
                "raw_text_payload": meta["raw_text_payload"],
            })

        # Upsert preserves prior SQLite INSERT OR REPLACE behavior.
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=payload_metas,
        )

    def get_all_vectors(self) -> tuple[list[str], np.ndarray, list[dict]]:
        """Return all stored ids, vectors, and metadata dicts."""
        records = self._collection.get(include=["embeddings", "metadatas", "documents"])
        ids = records.get("ids")
        if ids is None:
            ids = []
        if not ids:
            return [], np.array([]), []

        vecs = records.get("embeddings")
        if vecs is None:
            vecs = []
        metadatas = records.get("metadatas")
        if metadatas is None:
            metadatas = []
        documents = records.get("documents")
        if documents is None:
            documents = []

        metas = []
        for idx, meta in enumerate(metadatas):
            safe_meta = meta or {}
            payload = safe_meta.get("raw_text_payload")
            if not payload and idx < len(documents):
                payload = documents[idx]
            metas.append({
                "source_document":  safe_meta.get("source_document", ""),
                "chunk_index":      safe_meta.get("chunk_index", -1),
                "source_type":      safe_meta.get("source_type", "unknown"),
                "raw_text_payload": payload,
            })

        return ids, np.array(vecs, dtype=np.float32), metas

    def query(
        self,
        query_vector: np.ndarray,
        k: int = 4,
        distance_threshold: float = DISTANCE_THRESHOLD,
    ) -> dict:
        """
        Find top-k most similar chunks by cosine similarity.

        Returns
        -------
        dict with keys:
            "ids"       : list[str]
            "distances" : list[float]  (1 - cosine_similarity, lower = closer)
            "metadatas" : list[dict]
        """
        query_payload = self._collection.query(
            query_embeddings=[np.asarray(query_vector, dtype=np.float32).tolist()],
            n_results=k,
            include=["metadatas", "distances", "documents"],
        )

        ids_nested = query_payload.get("ids")
        if ids_nested is None:
            ids_nested = [[]]
        dists_nested = query_payload.get("distances")
        if dists_nested is None:
            dists_nested = [[]]
        metas_nested = query_payload.get("metadatas")
        if metas_nested is None:
            metas_nested = [[]]
        docs_nested = query_payload.get("documents")
        if docs_nested is None:
            docs_nested = [[]]

        if not ids_nested or not ids_nested[0]:
            return {"ids": [], "distances": [], "metadatas": []}

        result_ids = ids_nested[0]
        result_dists = [float(d) for d in dists_nested[0]]

        result_metas = []
        for idx, meta in enumerate(metas_nested[0]):
            safe_meta = meta or {}
            payload = safe_meta.get("raw_text_payload")
            if not payload and docs_nested and docs_nested[0] and idx < len(docs_nested[0]):
                payload = docs_nested[0][idx]
            result_metas.append({
                "source_document": safe_meta.get("source_document", ""),
                "chunk_index": safe_meta.get("chunk_index", -1),
                "source_type": safe_meta.get("source_type", "unknown"),
                "raw_text_payload": payload,
            })

        # Log quality gate warnings
        if all(d > distance_threshold for d in result_dists):
            logger.warning(
                "QUALITY GATE: all top-%d results have distance > %.2f. "
                "Query may be out-of-scope or corpus chunks are structurally flawed.",
                k, distance_threshold,
            )

        return {
            "ids":       result_ids,
            "distances": result_dists,
            "metadatas": result_metas,
        }

    def clear(self):
        ids = self._collection.get(include=[]).get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        logger.info("VectorStore cleared.")

    def close(self):
        # ChromaDB persistent client does not require explicit close.
        return None


# ─── Embedding Model (sentence-transformers) ──────────────────────────────────

class EmbeddingModel:
    """
    Wrapper around sentence-transformers/all-MiniLM-L6-v2.

    Produces L2-normalised 384-dim dense vectors. Cosine similarity between
    any two vectors maps to [0, 1]. Pre-trained — no corpus fit required.
    """

    def __init__(self):
        logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2)…")
        self._model = SentenceTransformer("all-MiniLM-L6-v2")

    def fit(self, texts: list[str]) -> None:
        logger.info("EmbeddingModel.fit() — model is pre-trained, no-op.")

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised embedding matrix, shape (n, 384)."""
        return self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


# ─── Source type classifier ───────────────────────────────────────────────────

_SOURCE_TYPE_MAP = {
    "ap_":          "news_wire",
    "guardian":     "news_analysis",
    "arxiv":        "preprint",
    "pubmed":       "peer_reviewed",
    "pmc":          "peer_reviewed",
    "world_bank":   "statistical_database",
    "wdi_":         "statistical_database",
    "unesco":       "statistical_database",
    "pew":          "public_opinion_survey",
    "statista":     "market_intelligence",
    "nist":         "government_framework",
}

def _infer_source_type(source_name: str) -> str:
    lower = source_name.lower()
    for key, stype in _SOURCE_TYPE_MAP.items():
        if key in lower:
            return stype
    return "unknown"


def _make_chunk_id(source: str, chunk_index: int) -> str:
    raw = f"{source}::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─── Public API ───────────────────────────────────────────────────────────────

def embed_and_store(
    chunks: list[dict],
    collection_name: str,
    vectorstore_dir: str = "vectorstore",
    model: Optional[EmbeddingModel] = None,
) -> tuple[EmbeddingModel, VectorStore]:
    """
    Embed chunks and store them with full metadata in the vector store.

    Parameters
    ----------
    chunks           : output of chunk.chunk_text()
    collection_name  : logical name for this embedding run
    vectorstore_dir  : directory for the ChromaDB persistence and model weights
    model            : pre-fitted EmbeddingModel (if None, one is fitted here)

    Returns
    -------
    (EmbeddingModel, VectorStore) — both ready for retrieval
    """
    Path(vectorstore_dir).mkdir(parents=True, exist_ok=True)
    db_path = str(Path(vectorstore_dir) / f"{collection_name}.db")

    texts = [c["text"] for c in chunks]

    # Fit (or reuse) embedding model
    if model is None:
        model = EmbeddingModel()
        model.fit(texts)
    else:
        logger.info("Reusing pre-fitted embedding model.")

    # Encode all chunks
    logger.info("Encoding %d chunks…", len(chunks))
    vectors = model.encode(texts)

    # Build vector store
    store = VectorStore(db_path)
    store.clear()

    ids       = [_make_chunk_id(c["source"], c["chunk_index"]) for c in chunks]
    metadatas = [
        {
            "source_document":  c["source"],
            "chunk_index":      c["chunk_index"],
            "source_type":      _infer_source_type(c["source"]),
            "raw_text_payload": c["text"],
        }
        for c in chunks
    ]

    store.add(ids, vectors, metadatas)

    # Integrity assertion (planning.md: Challenge 1 mitigation)
    stored_count = store.count()
    assert stored_count == len(chunks), (
        f"METADATA PIPELINE FAILURE: stored {stored_count} vectors "
        f"but expected {len(chunks)}. Check add() call."
    )
    logger.info(
        "✓ Integrity check passed: %d vectors stored with full metadata.",
        stored_count,
    )

    # Spot-check metadata completeness
    _, _, spot_metas = store.get_all_vectors()
    for i, m in enumerate(spot_metas):
        assert m.get("source_document"), f"Vector {i} missing source_document"
        assert m.get("raw_text_payload"), f"Vector {i} missing raw_text_payload"
    logger.info("✓ Metadata spot-check passed on all %d stored vectors.", len(spot_metas))

    return model, store


if __name__ == "__main__":
    # Smoke test
    from chunk import chunk_text

    sample_docs = [
        {"source": "nist_ai_rmf_2026.txt", "text":
         "The NIST AI Risk Management Framework prescribes factual accuracy rate, "
         "groundedness score, and refusal rate as the three primary metrics for "
         "evaluating generative AI hallucinations. Organizations must log each test "
         "run in a standardised audit trail with timestamp, model version, and verdict."},
        {"source": "pew_research_2026.txt", "text":
         "According to the 2026 Pew Research Center survey, public trust in "
         "technological innovation declined by 8 percentage points among adults "
         "aged 18-34, driven primarily by concerns over AI-generated misinformation."},
    ]

    chunks = chunk_text(sample_docs)
    model, store = embed_and_store(chunks, "smoke_test")

    print(f"\nStored {store.count()} vectors.")
    qv = model.encode_one("hallucination metrics for AI systems")
    results = store.query(qv, k=2)
    for dist, meta in zip(results["distances"], results["metadatas"]):
        print(f"\n  dist={dist:.3f} | source={meta['source_document']}")
        print(f"  {meta['raw_text_payload'][:100]}…")
