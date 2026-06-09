# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---
Global Research & Institutional Knowledge (AI Safety, Economic Data, Scientific Findings, International Policy)

**The Unofficial Guide** covers global research, economic, and AI-policy knowledge — spanning sources like UNESCO, NIST, World Bank, arXiv, and Pew Research — that are individually authoritative but institutionally siloed. A researcher asking how NIST AI hallucination metrics relate to current R&D investment trends has no single place to look: each organization publishes independently, uses incompatible methodologies, and never cross-references the others. The Unofficial Guide closes that gap by building a grounded Q&A layer over a multi-source corpus, with mandatory source attribution so every answer is traceable back to the specific document it came from.
## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |

---
The corpus spans four knowledge verticals to support cross-domain synthesis queries:

**General & International News**
- The Associated Press (AP) — wire reports on international trade regulations enacted Q1 2026
- The Guardian — in-depth coverage of Sub-Saharan African macroeconomic trends and debt shifts

**Scientific & Academic Research**
- arXiv preprints (2026) — early-access research on room-temperature superconductivity materials
- PubMed Central (PMC) — peer-reviewed biomedical literature on toxicity of superconducting materials

**Data & Economic Statistics**
- World Bank Open Data — `wdi_sub_saharan_debt_gdp_2024_2026.csv` (debt-to-GDP indicators by country)
- UNESCO Institute for Statistics 2026 R&D release — global GDP percentage allocated to R&D
- Pew Research Center — public trust in technological innovation (2026 survey data)
- Statista market reports — trade regulation compliance deadlines Q1 2026

**Technology & Policy**
- NIST AI Risk Management Framework (2026 update) — specific metrics for evaluating generative AI hallucinations and documentation requirements

*Source variety rationale:* Sources intentionally span news wire, peer-reviewed journals, preprint repositories, government statistical databases, nonpartisan polling, and market intelligence platforms. This maximizes the system's ability to handle cross-domain synthesis questions and exposes retrieval quality issues that a single-domain corpus would mask.
## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->
**Method:** Recursive character splitter with paragraph-level semantic boundaries
**Chunk size:**
300 tokens (~1,200 characters)
**Overlap:**
15% → 45 tokens (~180 characters)
**Reasoning:**
The corpus is heterogeneous: it includes short AP wire paragraphs (2–4 sentences), dense academic abstracts (6–10 sentences with statistical citations), and structured data narratives from World Bank and Statista. A single mechanical fixed-size split would slice statistical tables and referenced figures across chunk boundaries, destroying the semantic signal needed for retrieval.

A recursive character splitter respects natural boundaries in this order: `\n\n` (paragraph) → `\n` (line break) → `. ` (sentence) → ` ` (word). This ensures that a statistic like "Sub-Saharan debt-to-GDP rose 6.2% in Rwanda (World Bank, 2026)" is never split across two chunks.

**Why 300 tokens?**
- Too small (< 150 tokens): Short AP paragraphs would be further fragmented, destroying their news context (who, what, when, where). Retrieval would surface fragments without resolution.
- Too large (> 500 tokens): Dense academic sections would bundle multiple distinct claims into one chunk, causing the retrieval system to retrieve an entire subsection when only one sentence is relevant, inflating context noise.
- 300 tokens keeps most self-contained academic statements and news paragraphs intact as a single chunk.

**Why 15% overlap?**
If a NIST metric definition spans the last two sentences of one chunk and the first two of the next, the 45-token overlap ensures both chunks contain enough of that definition to cross the cosine similarity retrieval threshold when queried. Without overlap, one chunk would have a dangling reference ("as defined above…") with no retrievable antecedent.

**Volume sanity check (from documentation constraints):**
- Estimated total chunks: ~400–900 across all 10 documents (well within the 50–2,000 guardrail range)
- If chunks fall below 50: chunk size is too large → reduce to 150 tokens
- If chunks exceed 2,000: chunk size is too small or source material over-ingested → prune to core documents
---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
`all-MiniLM-L6-v2` via `sentence-transformers`                              **Why this model?**
- Produces dense 384-dimensional vectors optimized for semantic similarity across short-to-medium English passages
- Runs fully locally (no API cost per query), enabling deterministic and reproducible embedding at ingestion time
- Trained on diverse corpora including news, scientific text, and Q&A pairs — well-suited to this heterogeneous corpus
**Top-k:**
`k = 4`                                                                        - k = 2–3: Risks starving the LLM of cross-source context needed for synthesis questions (e.g., a NIST + Pew cross-domain question needs at least one chunk from each source)
- k = 4: Provides enough context for two-source synthesis while staying within a budget that avoids the "lost in the middle" phenomenon
- k ≥ 6: Marginal chunks with distance scores approaching 0.6 begin to introduce semantic noise; the LLM statistically attends less to context positioned in the middle of a long prompt
**Production tradeoff reflection:**
**Quality gate:** Distance scores > 0.6 (cosine or L2) are flagged as weak matches. Any query returning all top-4 chunks above this threshold triggers a refusal response rather than a speculative answer.

**Vector store:** ChromaDB (in-memory instance, persisted to disk between sessions)

**Metadata injected at ingestion (mandatory):**
```json
{
  "source_document": "nist_ai_rmf_2026.pdf",
  "chunk_index": 22,
  "source_type": "government_framework",
  "raw_text_payload": "..."
}
```

**Real-world tradeoffs (if cost were not a constraint):**
- `text-embedding-3-large` (OpenAI): Higher accuracy on domain-specific scientific text; 3,072-dimensional vectors improve precision but add latency and API cost per query
- `multilingual-e5-large`: Necessary if the corpus includes non-English UNESCO or World Bank reports
- Cohere Embed v3: Supports compressed int8 embeddings, reducing ChromaDB memory footprint for large corpora
---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---
Five verifiable test questions with expected correct answers:

**Q1 — Cross-domain synthesis**
*Question:* "According to the 2026 UNESCO Institute for Statistics release, what is the current global percentage of GDP allocated to R&D, and how does this statistical trend align with public trust sentiments on technological innovation from the Pew Research Center?"

*Expected answer:* States the specific UNESCO R&D GDP percentage from the 2026 release, then references the Pew sentiment data (direction of trust trend — increasing/decreasing). Both claims cite their respective source documents. The LLM does NOT extrapolate causal relationships beyond what is stated.

---

**Q2 — Contradictory information resolution**
*Question:* "Compare early arXiv findings on room-temperature superconductivity (2026 preprints) with the peer-reviewed PubMed Central consensus on the same materials' human toxicity. How do their conclusions differ?"

*Expected answer:* Identifies arXiv's preliminary claims on superconducting properties and PMC's peer-reviewed findings on toxicity (potentially contradictory). Response explicitly names both source documents, characterizes the nature of the disagreement, and does not resolve the scientific dispute beyond what the texts state.

---

**Q3 — Technical framework application**
*Question:* "What specific metrics does the NIST AI Risk Management Framework prescribe for evaluating generative AI hallucinations, and how should an organization document these tests?"

*Expected answer:* Lists the exact metrics named in the NIST document (e.g., factual accuracy rate, groundedness score, refusal rate on out-of-scope queries) and the prescribed documentation format or audit trail structure. Answer is fully bounded to the NIST chunks retrieved; no additional AI safety knowledge is injected.

---

**Q4 — Regional economic trend extraction**
*Question:* "Based on World Bank Open Data, which Sub-Saharan African countries showed a debt-to-GDP ratio increase exceeding 5% between 2024 and 2026, and what macroeconomic drivers did The Guardian attribute to this shift?"

*Expected answer:* Names specific countries from the World Bank dataset meeting the 5% threshold, then references The Guardian's attribution of macroeconomic drivers. If the World Bank data does not include specific country names in the ingested chunks, the system responds: "I do not have enough information to answer this question."

---

**Q5 — Out-of-scope refusal (adversarial)**
*Question:* "What were the top five AI product launches announced at CES 2026?"

*Expected answer:* System returns the exact refusal string: "I do not have enough information to answer this question." This question is intentionally out-of-scope (not covered by any ingested document). A successful refusal proves the grounding constraints are working. Any hallucinated product name is a critical failure.
## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---
**Challenge 1: Metadata pipeline silent failures**

If `chunk_index` or `source_document` metadata is not programmatically injected at ingestion time (e.g., because ChromaDB's `add()` call omits the `metadatas=` argument), the generation stage will have no source attribution to cite. The failure is silent — the LLM will still produce an answer, but it will be unverifiable. 

*Mitigation:* Write an ingestion unit test that asserts every stored vector has a non-null `source_document` and `raw_text_payload` field before the pipeline proceeds to any retrieval.

**Challenge 2: Cross-source chunk boundary splitting**

The World Bank dataset, when loaded as a structured CSV or tabular narrative, may be split such that a country name lands in one chunk and its corresponding debt ratio value lands in the next. A retrieval query for "Rwanda debt-to-GDP" may return only the chunk with Rwanda's name but not its numeric value, producing a retrieval hit that leads to an incomplete answer.

*Mitigation:* Serialize tabular data as complete row-level sentences before chunking (e.g., "Rwanda's debt-to-GDP ratio increased by 6.2 percentage points between 2024 and 2026 (World Bank Open Data)."). This converts tabular structure into self-contained semantic units that survive chunking intact.

**Challenge 3: Weak cosine similarity on highly technical queries**

NIST framework language is bureaucratic and technical ("trustworthy AI governance documentation protocols"). User queries are likely to be phrased colloquially ("how do I test my AI for hallucinations?"). Vocabulary mismatch between query and chunk can produce high distance scores even when the chunk is the correct answer.

*Mitigation:* Experiment with query expansion — prepend "According to official government AI safety guidelines:" to technical queries — to bias the embedding toward the document's register. If distance scores remain above 0.6 on Q3, increase chunk overlap to 25%.
## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
**Stage 1 — Ingestion preprocessing (`ingest.py`)**
Input to AI: The "Pipeline Stage 1" section of the technical documentation, the list of source URLs, and a description of the target data format (plain text paragraphs with metadata tags).
Expected output: A Python function `load_and_clean(source_path: str) -> list[dict]` that strips HTML entities, routes PDFs to `pdfplumber`, and returns a list of `{"text": str, "source": str}` dicts. Will prompt Claude with: *"Implement a Python ingestion function based on this spec. Use pdfplumber for PDFs. Strip HTML entities. Return a list of dicts with 'text' and 'source' keys. Handle the edge case where pdfplumber returns an empty string and raise a ValueError."*

**Stage 2 — Chunking (`chunk.py`)**
Input to AI: The "Chunking Strategy" section of this planning.md and the Stage 2 spec from the technical documentation.
Expected output: A `chunk_text(docs: list[dict], chunk_size: int, overlap: int) -> list[dict]` function using `langchain.text_splitter.RecursiveCharacterTextSplitter`. Will prompt Claude with: *"Implement chunk_text() using LangChain's RecursiveCharacterTextSplitter with chunk_size=300 tokens and overlap=45 tokens. Preserve the 'source' metadata from the input dict in each output chunk. Return chunks as a list of dicts with 'text', 'source', and 'chunk_index' keys."*
**Milestone 4 — Embedding and retrieval:(`embed.py`)**
Input to AI: Stage 3 spec from the technical documentation, the required metadata schema (source_document, chunk_index, raw_text_payload), and the chunk output format from Stage 2.
Expected output: An `embed_and_store(chunks: list[dict], collection_name: str)` function that encodes with `sentence-transformers/all-MiniLM-L6-v2` and calls `collection.add()` with correctly structured `metadatas=` argument. Will prompt Claude with: *"Implement embed_and_store() using sentence-transformers and ChromaDB. Inject the metadata schema exactly as specified. Include an assertion after insertion that verifies the stored vector count matches the input chunk count."*
**Milestone 5 — Generation and interface: (`generate.py`)**
Input to AI: The adversarial system prompt from Stage 5 of the technical documentation and the Groq API interface spec.
Expected output: A `generate_answer(query: str, context_chunks: list[dict]) -> str` function that formats context chunks with inline source labels, calls `llama-3.3-70b-versatile` via Groq, and returns both the answer string and a list of cited sources. Will prompt Claude with: *"Implement generate_answer() using the Groq Python SDK with model llama-3.3-70b-versatile. Use exactly the system prompt from the spec. Format each context chunk as '[Source: {source_document}] {raw_text_payload}' before injection. Return a tuple of (answer_text, cited_sources_list)."*

**Evaluation harness (`evaluate.py`)**
Input to AI: The five test questions and expected answer criteria from this planning.md.
Expected output: A test runner that calls the full pipeline for each question, prints the retrieved chunks (with distance scores), the LLM response, and prompts for a manual Accurate / Partially Accurate / Inaccurate / Correct Refusal verdict. Will prompt Claude with: *"Build an evaluation script that loops through the 5 test questions, calls the full pipeline, displays the top-4 retrieved chunks with their distance scores, displays the LLM answer, and prompts the user to enter a verdict. Log results to a CSV."*