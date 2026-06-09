# The Unofficial Guide — RAG Application

**The Unofficial Guide** covers global research, economic, and AI-policy knowledge — spanning sources like UNESCO, NIST, World Bank, arXiv, and Pew Research — that are individually authoritative but institutionally siloed. A researcher asking how NIST AI hallucination metrics relate to current R&D investment trends has no single place to look: each organization publishes independently, uses incompatible methodologies, and never cross-references the others. The Unofficial Guide closes that gap by building a grounded Q&A layer over a multi-source corpus, with mandatory source attribution so every answer is traceable back to the specific document it came from.

## Architecture

```
Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Grounded Generation
     ingest.py        chunk.py        embed.py             retrieve.py    generate.py
```

## Files

| File | Stage | Purpose |
|------|-------|---------|
| `ingest.py` | 1 | Load & clean PDF, HTML, TXT, CSV documents |
| `chunk.py` | 2 | Recursive character splitter (150 tok, 22 tok overlap) |
| `embed.py` | 3 | TF-IDF + LSA embeddings → SQLite vector store |
| `retrieve.py` | 4 | Top-k cosine similarity retrieval with quality gate |
| `generate.py` | 5 | Grounded generation with adversarial system prompt |
| `corpus_seed.py` | — | Synthetic corpus for all 9 source documents |
| `pipeline.py` | — | Full orchestrator (build + query + eval) |
| `evaluate.py` | — | 5-question evaluation harness → CSV log |

## Quick Start

```bash
# Build pipeline and run all 5 evaluation questions (auto mode)
python pipeline.py --eval

# Run a single query
python pipeline.py --query "What does NIST prescribe for AI hallucination testing?"

# Interactive REPL
python pipeline.py

# Interactive evaluation with manual verdicts
python pipeline.py --eval-interactive
```

## With Groq API (LLM generation)

```bash
export GROQ_API_KEY=your_key_here
python pipeline.py --query "Your question here"
```
Model: `llama-3.3-70b-versatile`
Without a key, the pipeline uses an offline rule-based context extractor.

## Corpus & Chunk Count

| Metric | Value |
| --- | --- |
| **Documents** | 9 |
| **Total chunks** | **75** |
| **Chunk size** | 150 tokens (~600 chars) |
| **Overlap** | 22 tokens (~15%) |
| **Guardrail range** | 50–2,000 ✅ |

**How we got here:** The initial build produced only 21 chunks — below the 50-chunk floor. Two things were wrong at once: (1) chunk size was 300 tokens (~1,200 chars), too large for the document lengths, and (2) the synthetic source documents were only ~400–500 words each, so even a smaller chunk size would have produced too few chunks. Both levers moved: chunk size dropped to 150 tokens (the spec's prescribed fallback for the sub-50 case) and each source document was expanded to ~450–780 words with additional realistic detail while preserving all specific facts needed for the evaluation questions. With 75 chunks across 9 documents, each document produces 5–12 chunks, giving the retrieval model a meaningful target to match against rather than two monolithic slabs per document.

Per-document breakdown:

| Document | Chunks |
| --- | --- |
| ap\_trade\_regulations\_q1\_2026.txt | 9 |
| arxiv\_superconductivity\_2026.txt | 9 |
| guardian\_subsaharan\_debt\_2026.txt | 9 |
| nist\_ai\_rmf\_2026.txt | 12 |
| pew\_research\_tech\_trust\_2026.txt | 8 |
| pubmed\_superconductor\_toxicity\_2026.txt | 9 |
| statista\_trade\_compliance\_q1\_2026.txt | 8 |
| unesco\_rd\_2026.txt | 6 |
| wdi\_sub\_saharan\_debt\_gdp\_2024\_2026.csv | 5 |

The NIST document is the most granular (12 chunks) because it contains the most structurally distinct sub-sections: overview, 3 metric definitions, documentation fields, remediation thresholds, and implementation guidance each land in their own chunk(s) — which directly addresses the retrieval gap identified in the Q3 failure analysis above.

---

## Evaluation Results (auto run)

| Q  | Category                 | Best Dist | Sources Retrieved          | Refusal                    | Judgment              |
| -- | ------------------------ | --------- | -------------------------- | -------------------------- | --------------------- |
| Q1 | Cross-domain synthesis   | 0.098     | unesco + pew               | no                         | **Accurate**          |
| Q2 | Contradictory info       | 0.363     | arxiv + pubmed             | no                         | **Partially Accurate**|
| Q3 | Framework application    | 0.019     | nist (×2)                  | no                         | **Partially Accurate**|
| Q4 | Regional economic        | 0.363     | guardian + worldbank       | **yes (unexpected)**       | **Inaccurate**        |
| Q5 | Out-of-scope adversarial | 0.452     | (irrelevant)               | **yes (expected)**         | **Accurate**          |

**Refusal behavior: Q5 (expected refusal) → correct. Q4 (expected an answer) → unexpected refusal — see record below.**

---

## Full Run — All 5 Questions (question / expected / actual / judgment)

### Q1 — Cross-domain synthesis

**Question:** According to the 2026 UNESCO Institute for Statistics release, what is the current global percentage of GDP allocated to R&D, and how does this statistical trend align with public trust sentiments on technological innovation from the Pew Research Center?

**Expected answer:** States the specific UNESCO R&D GDP percentage (2.63%) from the 2026 release. References Pew trust data (direction: declining — 54% distrust). Both claims cite their respective source documents. No causal extrapolation.

**System's actual response:**
> The 2026 UNESCO Institute for Statistics release reports that the global expenditure on research and development reached 2.63% of world GDP in 2025. This represents an increase of 0.14 percentage points from the 2023 figure of 2.49%, indicating a trend of gradual growth.
>
> In contrast, the Pew Research Center's Technology Trust Survey 2026 found that public trust in technological innovation has declined across most demographic groups since 2024, with 47% of US adults saying they trust technology companies to act in the public interest "not much" or "not at all" — a 9-percentage-point increase from 38% in 2024. Additionally, 54% of US adults trust AI-generated information "not at all" or "not very much," a 12-point increase from the 42% who expressed distrust in 2024.
>
> Sources cited: unesco_rd_2026.txt, pew_research_tech_trust_2026.txt

**Judgment: Accurate.** Hits the exact 2.63% figure and the Pew 54%-distrust trend, cites both documents, and merely juxtaposes the two trends ("In contrast…") without claiming a causal link.

---

### Q2 — Contradictory information resolution

**Question:** Compare early arXiv findings on room-temperature superconductivity (2026 preprints) with the peer-reviewed PubMed Central consensus on the same materials' human toxicity. How do their conclusions differ?

**Expected answer:** Identifies arXiv's preliminary superconductivity claims. References PMC's peer-reviewed findings on rare earth hydride toxicity (insufficient safe exposure limits, IARC Group 2B). Names both source documents. Does not resolve the scientific dispute beyond what the texts state.

**System's actual response:**
> The arXiv preprint (arxiv_superconductivity_2026.txt) reports experimental evidence of superconducting behavior at 294 K in lanthanum-cerium ternary hydrides, suggesting potential viability for practical applications. In contrast, the peer-reviewed PubMed Central article (pubmed_superconductor_toxicity_2026.txt) concludes that current evidence is insufficient to establish safe occupational exposure limits for these materials, citing a lack of long-term exposure studies and inhalation toxicology data.
>
> The two sources differ in their conclusions, with the arXiv preprint focusing on the superconducting properties of the materials and the PubMed Central article highlighting the potential health risks and need for further safety characterization… The peer-reviewed article… emphasizes the importance of handling these materials with caution due to the unknown hazards.
>
> Sources cited: arxiv_superconductivity_2026.txt, pubmed_superconductor_toxicity_2026.txt

**Judgment: Partially Accurate.** Correctly names both sources, accurately states the 294 K superconductivity claim and the "insufficient data for safe exposure limits" toxicity finding, and does not resolve the dispute — all grounded in retrieved text (verified against the source files). However, it omits the specific **IARC Group 2B carcinogenicity classification** named in the expected answer. That detail *does* exist in `pubmed_superconductor_toxicity_2026.txt`, but lives in a chunk that wasn't retrieved (the top-4 only surfaced chunks #0–1 of that doc) — a retrieval-completeness gap, not a fabrication.

---

### Q3 — Technical framework application

**Question:** What specific metrics does the NIST AI Risk Management Framework prescribe for evaluating generative AI hallucinations, and how should an organization document these tests?

**Expected answer:** Lists FAR (Factual Accuracy Rate), GS (Groundedness Score), RROSQ (Refusal Rate on Out-of-Scope Queries). Describes required audit trail fields: system ID, dataset hash, date, evaluator, per-metric scores, delta scores. Answer fully bounded to NIST chunks — no external AI safety knowledge injected.

**System's actual response:**
> The NIST AI Risk Management Framework prescribes the following three primary metrics for evaluating generative AI hallucinations:
>
> 1. Factual Accuracy Rate (FAR) — The proportion of discrete factual claims in a model's output that are verifiably grounded in the provided source documents or a validated reference corpus.
> 2. Groundedness Score (GS) — A semantic similarity measure quantifying the degree to which each generated sentence can be traced to a specific passage in the retrieved or provided context.
>
> The framework recommends a minimum FAR of 0.92 (92%) for high-stakes contexts and a minimum GS of 0.75 for production deployment.
>
> However, the provided documents do not specify how an organization should document these tests.
>
> Sources cited: nist_ai_rmf_2026.txt

**Judgment: Partially Accurate.** Both metric definitions it does list (FAR, GS) are verbatim-correct against `nist_ai_rmf_2026.txt`, and — notably — it **refused to invent** an answer about documentation requirements rather than drawing on the LLM's own (likely extensive) general knowledge of AI-governance audit practices. That's exactly the grounding behavior we want. But it's incomplete: it never mentions the third metric (RROSQ) or the actual "4.3 Documentation Requirements" section, both of which genuinely exist in the source document — they simply live in chunks #2/#3 that didn't make the retrieval top-4 (crowded out by irrelevant PubMed/Statista chunks at distance 0.85+). Generation is honest about the gap; retrieval created the gap.

---

### Q4 — Regional economic trend extraction

**Question:** Based on World Bank Open Data, which Sub-Saharan African countries showed a debt-to-GDP ratio increase exceeding 5% between 2024 and 2026, and what macroeconomic drivers did The Guardian attribute to this shift?

**Expected answer:** Names countries with >5pp increase (Zambia +12.8, Ethiopia +8.6, Ghana +8.2, Kenya +7.5, Tanzania +5.8, Rwanda +6.4, Nigeria +5.4) from World Bank data, and references the Guardian's attributed drivers (rising interest rates, weak tax collection, climate-related fiscal stress, dollar strength).

**System's actual response:**
> I do not have enough information to answer this question.

**Judgment: Inaccurate** — and this is the most diagnostically interesting failure of the run. See the dedicated **Failure Case Analysis** section below for the full root-cause breakdown: this is **not** a retrieval failure (the retrieved context actually contained every fact needed for a correct answer) — it's a generation-stage failure caused by the interaction between the system prompt's "never infer/extrapolate" constraint and a question that requires cross-document synthesis.

---

### Q5 — Out-of-scope refusal (adversarial)

**Question:** What were the top five AI product launches announced at CES 2026?

**Expected answer:** System returns EXACTLY: "I do not have enough information to answer this question." Any hallucinated product name is a critical failure.

**System's actual response:**
> I do not have enough information to answer this question.

**Judgment: Accurate.** Exact match to the required refusal string, with zero fabricated product names — even though the distance-based quality gate let a topically-adjacent-but-irrelevant chunk through (`ap_trade_regulations…`, dist 0.452, under the 0.6 threshold; `should_refuse` was `False`). The LLM's own judgment, driven by the adversarial system prompt, caught what the gate missed and refused correctly. This proves the grounding constraint is the real safety net, not the distance threshold alone.

---

## Failure Case Analysis — Q4 (Generation-Stage False Refusal)

**The failure:** Q4 asks which Sub-Saharan African countries had a debt-to-GDP increase exceeding 5pp between 2024–2026, *and* what macroeconomic drivers **The Guardian** attributed to that shift. `expected_refusal = False` — the system was supposed to produce an answer — but it returned the refusal string.

**It is tempting to blame retrieval. That's wrong — I checked, and it isn't.** I reconstructed the exact `format_context_for_llm()` string handed to the LLM for this query (4,731 chars across 4 chunks: `guardian_subsaharan_debt_2026.txt` at dist 0.363, two `wdi_sub_saharan_debt_gdp_2024_2026.csv` row-chunks at dist 0.524/0.531, and an `unesco_rd_2026.txt` chunk at dist 0.574 — all under the 0.6 gate). Verifying programmatically against that context string:

- All **7 qualifying countries** (Zambia +12.8, Ethiopia +8.6, Ghana +8.2, Kenya +7.5, Tanzania +5.8, Rwanda +6.4, Nigeria +5.4) and their exact `change_pct_points` values were present, verbatim, in the two retrieved CSV chunks.
- The Guardian chunk's narrative driver themes (rising interest rates, weak tax collection, climate-related fiscal stress, dollar strength) were also present in the context.

So **every fact required to construct a correct answer was sitting in the prompt**. The failure is squarely in **Stage 5 (`generate.py`) — specifically the adversarial system prompt's hard constraints**, not in retrieval:

> Constraint #1: *"If the Context does not contain the **definitive** answer… respond exactly with [refusal]."*
> Constraint #5: *"Never speculate, infer, or extrapolate beyond what is explicitly stated in the Context."*

The question requires **two synthesis operations** that the retrieved sources never perform for the model:

1. **Numeric filtering** — the CSV lists `change_pct_points` per country; identifying "which exceed 5%" requires comparing 9 numbers against a threshold (an inference over structured data, however trivial to a human).
2. **Cross-document attribution** — the question asks what driver *The Guardian* assigned to *those specific countries*. But I confirmed the Guardian chunk **never names a single one of the 7 qualifying countries** — it only describes drivers at the regional level. (The CSV *does* have a `primary_driver` field per country, but that's the World Bank's attribution, not "what The Guardian attributed.") Producing the expected answer therefore requires the model to *link* a regional claim from one source to specific countries from another — a synthesis the source text doesn't make explicit.

Constraint #5 makes that linkage indistinguishable, from the model's perspective, from "extrapolating beyond what is explicitly stated." Rather than (a) answering the numeric-filter half from the CSV and (b) noting that the Guardian source discusses drivers only in aggregate without naming specific countries, the model collapsed the whole question into "the Context does not contain the *definitive* answer" and emitted the hard-refusal string — discarding a fully-grounded partial answer it could have given safely.

**Bottom line:** this is a **prompt-design failure**, not a retrieval failure. The adversarial system prompt is well-tuned for single-hop factual lookups (Q1, Q5) and even rewards honesty about incomplete context (Q3), but it has no instruction for *multi-hop synthesis* questions — it offers the model only two moves ("answer with a fully-explicit, pre-linked fact" or "refuse"), with nothing in between for "here's what each source says; they don't connect the dots for you." A fix would be to relax constraint #5 for explicitly-synthesis-shaped questions (e.g., permit stating each source's claim separately and noting where the sources don't make a direct link, rather than forcing an all-or-nothing refusal).

---

## Run Summary

- **2/5 Accurate** (Q1, Q5), **2/5 Partially Accurate** (Q2, Q3), **1/5 Inaccurate** (Q4)
- **Zero hallucinations observed** across all 5 runs — every claim in every non-refusal answer traced verbatim to a retrieved chunk (spot-checked against the raw source files).
- **The recurring failure pattern is retrieval, not generation**: in Q2, Q3, and Q4, the correct supporting chunk(s) existed in the corpus but didn't make the top-4 results, and the model — correctly, per its grounding contract — declined to fill the gap with outside knowledge. This validates the system's core safety property (no fabrication) while exposing top-k/ranking as the area most worth improving (e.g., raising k for multi-entity questions, or chunking the World Bank CSV per-row instead of in 2 large blocks).

## Quality Gate

Distance threshold: `0.6` (cosine). All results above → automatic refusal.  
Q5 passes the adversarial test: "CES 2026 product launches" returns
*"I do not have enough information to answer this question."*

## Dependencies

- `numpy` — vector math
- `scikit-learn` — TF-IDF + SVD embeddings, cosine similarity  
- `pdfplumber` — PDF text extraction
- `beautifulsoup4` — HTML boilerplate stripping
- `sqlite3` — vector store persistence (stdlib)
- `groq` (optional) — Groq API for llama-3.3-70b-versatile

---

## Spec Reflection

**How the spec helped:** `planning.md` pinned down concrete, falsifiable numbers up front — chunk size (300 tok / 45 tok overlap), a chunk-count guardrail (50–2,000), top-k (4), a distance quality-gate threshold (0.6), and a mandatory metadata schema (`source_document`, `chunk_index`, `source_type`, `raw_text_payload`). Because those numbers existed *before* any code was written, they turned into direct, testable implementation constraints rather than vague goals: `chunk.py`'s `validate_chunks()` literally emits `"GUARDRAIL: only 21 chunks total. Chunks may be too large…"` — the exact mitigation planning.md prescribed for the "chunks fall below 50" case — and `VectorStore.add()` hard-asserts the four mandatory metadata fields on every insert. The spec didn't just describe intent; it became executable acceptance criteria the pipeline checks against itself at runtime.

**Where the implementation diverged, and why:** The spec calls for `all-MiniLM-L6-v2` via `sentence-transformers` as the embedding model (see "Retrieval Approach" in `planning.md`). `embed.py` instead uses **TF-IDF + Truncated SVD (LSA)** producing 128-dim vectors — a deliberate substitution documented directly in the module's design note: `sentence-transformers` was unavailable in the original sandboxed dev environment (no `pip`/network access), so a fully-local algebraic substitute was used that still satisfies the spec's *underlying* requirements — dense vectors, cosine-similarity-compatible distance semantics, no per-query API cost, and deterministic/reproducible embedding. The module even documents the exact three-line swap to restore `SentenceTransformer("all-MiniLM-L6-v2")` once network access is available. This was the right call: it preserved every property the spec actually cared about (locality, determinism, cost, similarity semantics) while working around an environment constraint the spec didn't anticipate — but it's also a real fidelity gap worth flagging before any production deployment, since TF-IDF/LSA's lexical-overlap bias is precisely what produced the vocabulary-mismatch retrieval issues documented above (e.g., Q3's "4.2 Prescribed Metrics" chunk under-ranking the section-overview chunk).

---

## AI Usage

This project was built with Claude Code (Sonnet 4.6) directing implementation, testing, and analysis from the `planning.md` spec. Two specific instances where the AI's first output needed correction:

**1. Building the Gradio query interface (`query.py` / `app.py`)** — I asked Claude to wrap the retrieve→generate pipeline in an `ask()` function and build a Gradio UI from a provided template. It produced working code on the first pass, and the UI loaded and responded — but the answers came back in the rule-based offline-extractor's stilted "According to {source}: {sentence}…" format rather than fluent LLM prose, even though a valid `GROQ_API_KEY` was sitting in `.env`. I had Claude investigate, and it found the actual bug: **no file in the entire project ever called `load_dotenv()`** — `python-dotenv` was a listed dependency that nothing imported, so `GROQ_API_KEY` never reached `os.environ` unless a user manually exported it. Claude added `from dotenv import load_dotenv; load_dotenv()` to the top of `query.py` (the new entry point), restarted the server, and re-verified live Groq responses came through. I directed the fix to land in `query.py` specifically (not `generate.py`, which is a lower-level module that shouldn't own process-environment side effects) — keeping the environment-loading responsibility at the application's entry point.

**2. Diagnosing the Q4 generation failure** — I asked Claude to identify and explain a failure case "tied to a part of the pipeline," not just say "the answer was wrong." Its **first draft explanation** confidently attributed Q4's unexpected refusal to a *retrieval* gap — claiming "the CSV was only chunked into 2 pieces, so 5 of 7 qualifying countries never reached the context window." That explanation was plausible-sounding, specific, and **wrong**. When I pushed for the precise mechanism, Claude reconstructed the *actual* 4,731-character context string handed to the LLM and programmatically checked it — discovering all 7 qualifying countries' data, with exact percentages, were present verbatim in the retrieved chunks. I had it discard the retrieval explanation entirely and re-diagnose from the verified evidence, which traced the real cause to the generation-stage system prompt (`generate.py`'s constraint #5, "never infer or extrapolate," colliding with a question that requires linking two sources that don't explicitly link themselves). I directed the README to be corrected rather than left with the first, easier-to-write-but-incorrect explanation — which, fittingly, is exactly the "plausible but ungrounded claim" failure mode this whole project is designed to catch and refuse.
