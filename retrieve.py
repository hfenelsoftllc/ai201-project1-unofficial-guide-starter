"""
Stage 4 — Semantic Retrieval
The Unofficial Guide RAG Pipeline

Transforms user queries into dense vectors using the fitted EmbeddingModel,
performs cosine similarity search against the VectorStore, applies the
distance quality gate, and returns the top-k context chunks.
"""

import logging
from typing import Optional
import numpy as np

from embed import EmbeddingModel, VectorStore, DISTANCE_THRESHOLD

logger = logging.getLogger("retrieve")

# ─── Query expansion (planning.md: Challenge 3 mitigation) ───────────────────

_DOMAIN_PREFIXES = {
    "nist":       "According to official government AI safety guidelines:",
    "framework":  "According to official government AI safety guidelines:",
    "hallucin":   "According to official government AI safety guidelines:",
    "metric":     "According to official government AI safety guidelines:",
    "r&d":        "According to global research and development statistics:",
    "gdp":        "According to global economic statistics:",
    "debt":       "According to World Bank economic data:",
    "supercond":  "According to peer-reviewed and preprint scientific research:",
    "toxicity":   "According to biomedical research literature:",
    "trust":      "According to public opinion survey data:",
    "trade":      "According to international trade regulation reporting:",
}


def _expand_query(query: str) -> str:
    """
    Prepend a domain-register prefix to technical queries to reduce
    vocabulary mismatch between colloquial queries and formal document text.
    Returns the original query unchanged if no prefix matches.
    """
    lower = query.lower()
    for keyword, prefix in _DOMAIN_PREFIXES.items():
        if keyword in lower:
            expanded = f"{prefix} {query}"
            logger.debug("Query expanded: '%s' → '%s'", query[:60], expanded[:80])
            return expanded
    return query


# ─── Retrieval ────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    model: EmbeddingModel,
    store: VectorStore,
    k: int = 4,
    distance_threshold: float = DISTANCE_THRESHOLD,
    use_query_expansion: bool = True,
) -> dict:
    """
    Retrieve the top-k most relevant chunks for a user query.

    Parameters
    ----------
    query               : raw user question string
    model               : fitted EmbeddingModel (from embed stage)
    store               : populated VectorStore
    k                   : number of chunks to retrieve (default 4)
    distance_threshold  : max acceptable cosine distance (default 0.6)
    use_query_expansion : whether to apply domain-register prefix expansion

    Returns
    -------
    dict:
        "query"          : original query string
        "expanded_query" : query after optional expansion
        "results"        : list of dicts, each with:
            "rank"             : int (1-based)
            "distance"         : float (lower = more relevant)
            "source_document"  : str
            "chunk_index"      : int
            "source_type"      : str
            "raw_text_payload" : str
        "all_below_threshold" : bool  (True = quality gate triggered)
        "should_refuse"       : bool  (True = return refusal string)
    """
    if not query.strip():
        raise ValueError("Query string is empty.")

    expanded = _expand_query(query) if use_query_expansion else query
    query_vec = model.encode_one(expanded)

    raw = store.query(query_vec, k=k, distance_threshold=distance_threshold)

    results = []
    for rank, (dist, meta) in enumerate(
        zip(raw["distances"], raw["metadatas"]), start=1
    ):
        results.append({
            "rank":             rank,
            "distance":         dist,
            "source_document":  meta["source_document"],
            "chunk_index":      meta["chunk_index"],
            "source_type":      meta["source_type"],
            "raw_text_payload": meta["raw_text_payload"],
        })

    # Quality gate: if ALL results are weak matches, flag for refusal
    all_below = bool(results) and all(r["distance"] > distance_threshold for r in results)
    should_refuse = all_below or (len(results) == 0)

    if should_refuse:
        logger.warning(
            "Quality gate triggered for query: '%s…'. All distances > %.2f.",
            query[:60], distance_threshold,
        )
    else:
        best = results[0] if results else {}
        logger.info(
            "Retrieved %d chunks. Best: dist=%.3f, source='%s'",
            len(results),
            best.get("distance", 1.0),
            best.get("source_document", "—"),
        )

    return {
        "query":              query,
        "expanded_query":     expanded,
        "results":            results,
        "all_below_threshold": all_below,
        "should_refuse":      should_refuse,
    }


def format_context_for_llm(retrieval_result: dict) -> str:
    """
    Format retrieved chunks into the context block injected into the LLM prompt.

    Each chunk is labelled with its source document so the model can cite it.
    Format: [Source: {source_document}] {raw_text_payload}
    """
    if retrieval_result["should_refuse"] or not retrieval_result["results"]:
        return ""

    lines = ["=== CONTEXT ==="]
    for r in retrieval_result["results"]:
        lines.append(
            f"\n[Source: {r['source_document']}]\n{r['raw_text_payload']}"
        )
    lines.append("\n=== END CONTEXT ===")
    return "\n".join(lines)


if __name__ == "__main__":
    from chunk import chunk_text
    from embed import embed_and_store

    docs = [
        {"source": "nist_ai_rmf_2026.txt", "text":
         "The NIST AI Risk Management Framework (2026) prescribes three primary metrics "
         "for evaluating generative AI hallucinations: (1) Factual Accuracy Rate — the "
         "proportion of claims in model output that are verifiably grounded in source "
         "documents; (2) Groundedness Score — a semantic similarity measure between "
         "generated claims and retrieved context; (3) Refusal Rate on Out-of-Scope Queries "
         "— the fraction of queries outside the corpus for which the model correctly "
         "returns a refusal response. Documentation must include model version, test date, "
         "dataset hash, and per-metric score in a structured audit trail."},
        {"source": "pew_research_2026.txt", "text":
         "The 2026 Pew Research Center Technology Trust Survey found that 54% of US adults "
         "trust AI-generated information 'not at all' or 'not very much', a 12-point increase "
         "from 2024. Trust was lowest among adults aged 18-29 (62% distrust) and highest among "
         "adults over 65 (41% distrust). The primary driver cited was concern about AI-generated "
         "misinformation in news contexts."},
    ]
    chunks = chunk_text(docs)
    model, store = embed_and_store(chunks, "retrieve_test")

    q = "What metrics does NIST prescribe for hallucination testing?"
    result = retrieve(q, model, store)
    print(f"\nQuery: {q}")
    print(f"Should refuse: {result['should_refuse']}")
    for r in result["results"]:
        print(f"  rank={r['rank']} dist={r['distance']:.3f} "
              f"source={r['source_document']} idx={r['chunk_index']}")
    print()
    print(format_context_for_llm(result))
