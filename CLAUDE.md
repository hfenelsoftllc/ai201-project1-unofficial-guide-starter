# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Build the pipeline (ingests corpus, chunks, embeds, stores)
python pipeline.py

# Run a single query
python pipeline.py --query "What does NIST prescribe for AI hallucination testing?"

# Run the 5-question evaluation suite (auto mode — no manual verdicts)
python pipeline.py --eval

# Run evaluation interactively (prompts for verdict after each question)
python pipeline.py --eval-interactive

# Start the Gradio web UI on http://localhost:7860
python app.py

# Enable LLM generation (without key, uses offline rule-based fallback)
export GROQ_API_KEY=your_key_here
python pipeline.py --query "..."

# Run an individual module as a smoke test (each has an if __name__ == "__main__" block)
python embed.py
python retrieve.py
python generate.py
```

## Architecture

Five-stage RAG pipeline. Each stage lives in its own module and can be run independently:

```
corpus_seed.py  →  ingest.py  →  chunk.py  →  embed.py  →  retrieve.py  →  generate.py
  [seed docs]     [load/clean]   [split]     [embed+store]  [cosine sim]   [LLM answer]
```

`pipeline.py` is the orchestrator — it runs stages 1–3 at startup (always), then dispatches to query, eval, or REPL mode.

`query.py` is a thin wrapper that calls `build_pipeline()` lazily on first import and exposes a single `ask(question) -> dict` function. `app.py` (Gradio UI) calls `ask()` directly.

### Key design decisions

**Embedding model:** The spec called for `sentence-transformers/all-MiniLM-L6-v2` but `embed.py` uses **TF-IDF + Truncated SVD (LSA)** producing 128-dim L2-normalised vectors stored in ChromaDB. This was a deliberate substitution for offline dev. The 3-line swap to restore `SentenceTransformer` is documented in `embed.py`'s module docstring.

**Vector store:** ChromaDB `PersistentClient` backed by `vectorstore/chroma/`. The `VectorStore` class in `embed.py` hard-asserts four mandatory metadata fields (`source_document`, `chunk_index`, `source_type`, `raw_text_payload`) on every `add()` call.

**Quality gate:** Cosine distance threshold `0.6` (defined as `DISTANCE_THRESHOLD` in `embed.py`, imported by `retrieve.py` and `pipeline.py`). If all top-k results exceed this, `retrieve()` sets `should_refuse=True` and `generate_answer()` returns the hard refusal string verbatim.

**Generation:** Two modes determined by `GROQ_API_KEY` presence — Groq API (`llama-3.3-70b-versatile`, temperature 0.0) or offline rule-based extractor (`_offline_generate` in `generate.py`). The adversarial system prompt in `generate.py:SYSTEM_PROMPT` is the primary anti-hallucination control; it constrains the LLM to source-only answers and mandates a "Sources cited:" section.

**Query expansion:** `retrieve.py:_expand_query()` prepends domain-register prefixes to reduce vocabulary mismatch between colloquial queries and formal document text (e.g., queries containing "nist" or "hallucin" get an "According to official government AI safety guidelines:" prefix).

**Corpus:** `corpus_seed.py` generates the 9 synthetic source documents into `data/raw/` on first run if the directory is empty. Chunk parameters: 150 tokens, 22-token overlap, top-k = 4.

**Environment loading:** `load_dotenv()` is called at the top of `query.py` (the application entry point). Lower-level modules (`generate.py`, `pipeline.py`) do not own this side effect.

### Data flow for a query

1. `ask(question)` in `query.py` calls `retrieve(question, model, store)` → returns ranked chunks with distances
2. `generate_answer(question, retrieval_result)` checks `should_refuse`; if True returns refusal string
3. Otherwise calls `format_context_for_llm()` → formats chunks as `[Source: filename] text` block
4. Sends to Groq (or offline fallback) with the adversarial system prompt
5. Returns `(answer_text, cited_sources_list)`

## Known Failure Pattern

The adversarial system prompt's "never infer or extrapolate" constraint causes false refusals on multi-hop synthesis questions (where answers require comparing figures across two sources that don't cross-reference each other). The generation stage correctly refuses rather than hallucinating, but discards grounded partial answers it could safely give. See the Q4 analysis in `README.md` for the full diagnosis.
