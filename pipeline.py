"""
pipeline.py — Full Pipeline Orchestrator
The Unofficial Guide RAG Application

Runs all 5 stages sequentially:
  1. Ingest documents from data/raw/
  2. Chunk with recursive character splitter
    3. Embed + store in ChromaDB vector store
  4-5. Available interactively or via evaluate.py

Usage:
  python pipeline.py              # build the pipeline from corpus
  python pipeline.py --query "…"  # build + run a single query
  python pipeline.py --eval       # build + run full evaluation suite (auto mode)
  python pipeline.py --eval-interactive  # build + run evaluation with prompts
"""

import argparse
import logging
import sys
from pathlib import Path

# Force UTF-8 output on Windows (cp1252 default can't encode box-drawing/emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Configure logging before any imports that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline")


def build_pipeline(data_dir: str = "data/raw",
                   vectorstore_dir: str = "vectorstore",
                   collection_name: str = "unofficial_guide"):
    """Stages 1–3: ingest, chunk, embed, store."""
    from corpus_seed import seed_corpus
    from ingest import load_corpus, validate_docs
    from chunk import chunk_text, validate_chunks
    from embed import embed_and_store

    # ── Seed corpus if data dir is empty ──────────────────────────────────────
    raw_dir = Path(data_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing = [f for f in raw_dir.iterdir() if f.is_file()]

    if not existing:
        logger.info("Data directory is empty — seeding synthetic corpus…")
        seed_corpus(str(raw_dir))
    else:
        logger.info("Found %d existing files in '%s'", len(existing), data_dir)

    # ── Stage 1: Ingestion ────────────────────────────────────────────────────
    logger.info("\n[Stage 1] Document Ingestion")
    docs = load_corpus(data_dir)
    validate_docs(docs)
    logger.info("  → %d documents loaded and validated", len(docs))

    # ── Stage 2: Chunking ─────────────────────────────────────────────────────
    logger.info("\n[Stage 2] Chunking")
    chunks = chunk_text(docs, chunk_size=150, overlap=22)
    validate_chunks(chunks)
    logger.info("  → %d chunks produced", len(chunks))

    # ── Stage 3: Embedding + Vector Store ────────────────────────────────────
    logger.info("\n[Stage 3] Embedding + Vector Store")
    model, store = embed_and_store(
        chunks,
        collection_name=collection_name,
        vectorstore_dir=vectorstore_dir,
    )
    logger.info("  → %d vectors stored with metadata", store.count())

    return model, store


def run_query(query: str, model, store) -> None:
    """Stages 4–5: retrieve + generate for a single query."""
    from retrieve import retrieve, format_context_for_llm
    from generate import generate_answer
    from embed import DISTANCE_THRESHOLD

    print(f"\n{'─'*72}")
    print(f"Query: {query}")
    print(f"{'─'*72}")

    retrieval = retrieve(query, model, store)

    print("\n📦 Retrieved chunks:")
    for r in retrieval["results"]:
        quality = "✓" if r["distance"] < DISTANCE_THRESHOLD else "⚠"
        print(f"  {quality} rank={r['rank']} dist={r['distance']:.3f} "
              f"[{r['source_document']}] idx={r['chunk_index']}")
        print(f"    {r['raw_text_payload'][:150].replace(chr(10), ' ')}…")

    if retrieval["should_refuse"]:
        print("\n⚠ Quality gate triggered — returning refusal response.\n")

    print("\n🤖 Answer:")
    answer, sources = generate_answer(query, retrieval)
    print(answer)
    if sources:
        print(f"\n📎 Sources cited: {sources}")
    print()


def main():
    parser = argparse.ArgumentParser(description="The Unofficial Guide — RAG Pipeline")
    parser.add_argument("--data-dir",       default="data/raw",       help="Directory with source documents")
    parser.add_argument("--vectorstore-dir", default="vectorstore",   help="Directory for vector store")
    parser.add_argument("--collection",     default="unofficial_guide", help="Collection name")
    parser.add_argument("--query",          type=str, default=None,   help="Run a single query")
    parser.add_argument("--eval",           action="store_true",      help="Run evaluation suite (auto mode)")
    parser.add_argument("--eval-interactive", action="store_true",    help="Run evaluation suite (interactive)")
    args = parser.parse_args()

    # ── Always build pipeline first ───────────────────────────────────────────
    model, store = build_pipeline(
        data_dir=args.data_dir,
        vectorstore_dir=args.vectorstore_dir,
        collection_name=args.collection,
    )

    print(f"\n{'='*72}")
    print(f"  Pipeline ready -- {store.count()} chunks indexed.")
    print(f"{'='*72}\n")

    # ── Query mode ────────────────────────────────────────────────────────────
    if args.query:
        run_query(args.query, model, store)

    # ── Evaluation modes ──────────────────────────────────────────────────────
    elif args.eval or args.eval_interactive:
        from evaluate import main as eval_main
        eval_main(auto_mode=args.eval)

    # ── Interactive REPL ──────────────────────────────────────────────────────
    else:
        print("Type a question and press Enter. Type 'quit' to exit.\n")
        while True:
            try:
                query = input("❓ Query → ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                break
            run_query(query, model, store)


if __name__ == "__main__":
    main()
