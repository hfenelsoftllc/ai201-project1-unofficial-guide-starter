# Memory — AI201 Project 1: The Unofficial Guide RAG App

Last updated: 2026-06-30

## What was built

- **CLAUDE.md** — created from scratch; documents all run commands, 5-stage pipeline architecture, key design decisions, data flow, known failure pattern (marked mitigated)
- **Spec alignment refactor** — swapped `EmbeddingModel` in `embed.py` from TF-IDF+LSA (128-dim) to `sentence-transformers/all-MiniLM-L6-v2` (384-dim); removed pkl save/load; dropped sklearn imports
- **System prompt fix** — added constraint #6 to `SYSTEM_PROMPT` in `generate.py` to allow grounded per-source statements for multi-hop synthesis questions (fixes Q4 false-refusal)
- **Chunk defaults locked** — `chunk.py` defaults updated to 150 tokens / 22 overlap (from 300/45); `planning.md` updated to match
- **.gitignore** — added `vectorstore/` and `*.pkl` exclusions
- **10th document** — added `oecd_science_technology_2026.txt` to `corpus_seed.py` (OECD STI Outlook 2026: R&D investment, AI patents, researcher density)
- **planning.md** — filled in Architecture section with ASCII pipeline diagram; added OECD as document #10 in table and verticals list; updated chunk count to 10 documents
- **README.md** — added Ingestion Pipeline section (loader table + preprocessing); added Embedding Model & Production Tradeoffs section (comparison table); updated document count to 10
- **planning_before.md** — deleted (blank template was confusing the grader)
- **requirements.txt** — fixed: added `pdfplumber==0.11.4`, `beautifulsoup4>=4.12.0`, `lxml>=5.0.0`; uncommented `pdfplumber`

## Decisions made

- Chunk size stays at 150 tokens / 22 overlap — corpus math makes 300 tokens non-viable (only 2–3 chunks per doc)
- `sentence-transformers/all-MiniLM-L6-v2` is the canonical embedding model — pkl persistence removed since HuggingFace cache handles model weights
- `load_dotenv()` lives only in `query.py` (the application entry point) — lower-level modules do not own this side effect
- PRs on upstream (`jamjamgobambam`) cannot be merged by `hfenelsoftllc` — all changes applied directly to fork's main

## Problems solved

- Q4 false-refusal: adversarial system prompt's "never infer" constraint caused full refusal even when all required facts were in retrieved context — fixed by constraint #6 in `generate.py:SYSTEM_PROMPT`
- Sub-50 chunk guardrail: corpus was too small at 300 tokens → reduced to 150 tokens, expanded each source doc to ~500–780 words
- `GROQ_API_KEY` not loading: `load_dotenv()` was never called anywhere — fixed by adding it to top of `query.py`
- Grader confusion: `planning_before.md` (blank template) was in repo alongside `planning.md` — deleted
- `requirements.txt` missing deps: `ingest.py` imports `pdfplumber` and `BeautifulSoup` at top level but both were absent — added all three packages

## Current state

- **Fork (`hfenelsoftllc/main`)**: fully up to date with all changes, at commit `072dd58`
- **No open PRs** anywhere — upstream PR #44 and #45 both closed (no merge permissions on upstream)
- Clean working tree, no uncommitted changes
- `vectorstore/` is gitignored and will be rebuilt on next `python pipeline.py` run
- No stretch features implemented (hybrid search, chunking comparison, metadata filtering, conversational memory)

## Next session starts with

Run `python pipeline.py --eval` to verify sentence-transformers loads correctly and all 5 evaluation questions produce valid results without errors.

## Open questions

- Should any stretch features be implemented (hybrid search, chunking comparison, metadata filtering, conversational memory)?
- Confirm whether grader feedback is fully resolved now that `planning_before.md` is deleted and `requirements.txt` is fixed
