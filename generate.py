"""
Stage 5 — Grounded Generation
The Unofficial Guide RAG Pipeline

Calls the LLM with retrieved context and an adversarial system prompt
that hard-constrains the model to source-only answers.

Target: llama-3.3-70b-versatile via Groq API.
Fallback: rule-based context extractor (when GROQ_API_KEY is not set).

The fallback produces deterministic, context-bounded answers without
any LLM call — useful for testing the full pipeline offline.
"""

import os
import re
import logging
from typing import Optional

from retrieve import format_context_for_llm

logger = logging.getLogger("generate")

# ─── Adversarial system prompt (verbatim from planning.md spec) ───────────────

SYSTEM_PROMPT = """You are a strict QA engine. Answer the user question using ONLY the facts explicitly stated within the provided Context section below.

Constraints:
1. If the Context does not contain the definitive answer to the question, respond exactly with: "I do not have enough information to answer this question."
2. Do NOT use your own external knowledge or make logical assumptions.
3. Every claim you make must be directly traceable to a specific source document listed in the Context.
4. After your answer, list the source documents you cited under a heading "Sources cited:".
5. Never speculate, infer, or extrapolate beyond what is explicitly stated in the Context."""

REFUSAL_STRING = "I do not have enough information to answer this question."

PROMPT_TEMPLATE = """Use ONLY the information in the provided documents to answer the question.

Rules:
1. Do not use external knowledge.
2. If the documents do not contain enough information, respond exactly with:
   \"I do not have enough information to answer this question.\"
3. Keep the answer grounded in the documents.
4. After the answer, include a section titled \"Sources cited:\" listing the source documents you used.

Provided documents:
{context}

Question:
{question}
"""


def build_grounded_prompt(question: str, context: str) -> str:
    """Build the user prompt payload that enforces strict context-only answering."""
    return PROMPT_TEMPLATE.format(question=question, context=context)


# ─── Source citation extractor ────────────────────────────────────────────────

def _extract_cited_sources(answer: str, retrieval_results: list[dict]) -> list[str]:
    """
    Identify which source documents are referenced in the answer text.
    Checks both explicit mentions and the 'Sources cited:' section.
    """
    cited = set()

    # Check sources mentioned in answer text
    for r in retrieval_results:
        src = r["source_document"]
        src_base = src.lower().replace("_", " ").replace(".txt", "").replace(".pdf", "")
        if src.lower() in answer.lower() or src_base in answer.lower():
            cited.add(src)

    # Also pick up any "[Source: ...]" patterns the model may echo
    for match in re.finditer(r'\[Source:\s*([^\]]+)\]', answer, re.IGNORECASE):
        cited.add(match.group(1).strip())

    # Extract from "Sources cited:" block if present
    if "sources cited:" in answer.lower():
        sources_block = re.split(r'sources cited:', answer, flags=re.IGNORECASE)[-1]
        for line in sources_block.splitlines():
            line = line.strip("- •*\t ")
            if line and len(line) > 3:
                cited.add(line)

    return sorted(cited)


# ─── Offline fallback generator ───────────────────────────────────────────────

def _offline_generate(query: str, context_str: str, retrieval_results: list[dict]) -> str:
    """
    Rule-based context extractor used when Groq API key is unavailable.

    Refuses if no corpus sentence has >= 2 meaningful keyword overlaps with the query.
    This prevents out-of-scope queries (Q5 adversarial test) from returning corpus noise.
    """
    if not context_str or not retrieval_results:
        return REFUSAL_STRING

    # Meaningful content words only — exclude stopwords and short tokens
    _STOPWORDS = {
        "what", "were", "which", "have", "that", "this", "with", "from",
        "their", "they", "does", "each", "also", "been", "about", "than",
        "more", "some", "into", "when", "there", "would", "could", "should",
        "based", "show", "five", "three", "most", "data", "between",
        "rate", "2026", "2025", "2024", "year", "percent",
    }
    query_words = {
        w for w in re.findall(r'\b[a-z]{5,}\b', query.lower())
        if w not in _STOPWORDS
    }

    MIN_OVERLAP = 2  # require at least 2 shared content words

    scored_sentences = []
    for r in retrieval_results:
        text = r["raw_text_payload"]
        source = r["source_document"]
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 30:
                continue
            sent_words = set(re.findall(r'\b[a-z]{5,}\b', sent.lower()))
            overlap = len(query_words & sent_words)
            if overlap >= MIN_OVERLAP:
                scored_sentences.append((overlap, sent, source))

    if not scored_sentences:
        return REFUSAL_STRING

    scored_sentences.sort(key=lambda x: -x[0])
    top = scored_sentences[:4]

    answer_parts = []
    source_list  = []
    for _, sent, src in top:
        answer_parts.append(f"According to {src}: {sent}")
        if src not in source_list:
            source_list.append(src)

    answer = " ".join(answer_parts)
    answer += "\n\nSources cited:\n" + "\n".join(f"- {s}" for s in source_list)
    return answer


def _groq_generate(query: str, context_str: str) -> str:
    """Call Groq API with llama-3.3-70b-versatile."""
    try:
        import groq as groq_lib
    except ImportError:
        raise RuntimeError("groq package not installed. Install with: pip install groq")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set.")

    client = groq_lib.Groq(api_key=api_key)

    user_message = build_grounded_prompt(query, context_str)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_message},
        ],
        temperature=0.0,    # Deterministic — grounding requires no creativity
        max_tokens=1024,
    )

    return response.choices[0].message.content


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_answer(
    query: str,
    retrieval_result: dict,
    force_offline: bool = False,
) -> tuple[str, list[str]]:
    """
    Generate a grounded answer for the query given the retrieval result.

    Parameters
    ----------
    query            : original user question
    retrieval_result : output of retrieve.retrieve()
    force_offline    : skip Groq even if key is present (for testing)

    Returns
    -------
    (answer_text: str, cited_sources: list[str])

    The answer is REFUSAL_STRING if:
      - retrieval_result["should_refuse"] is True
      - all retrieved chunks have distance > threshold
      - no context chunks were returned
    """
    # Hard refusal: retrieval quality gate failed
    if retrieval_result.get("should_refuse", False):
        logger.info("Refusal triggered by quality gate for query: '%s…'", query[:60])
        return REFUSAL_STRING, []

    context_str = format_context_for_llm(retrieval_result)
    results     = retrieval_result.get("results", [])

    api_key     = os.environ.get("GROQ_API_KEY", "")
    use_groq    = bool(api_key) and not force_offline

    if use_groq:
        logger.info("Generating with Groq (llama-3.3-70b-versatile)…")
        try:
            answer = _groq_generate(query, context_str)
        except Exception as exc:
            logger.error("Groq call failed: %s. Falling back to offline generator.", exc)
            answer = _offline_generate(query, context_str, results)
    else:
        mode = "offline (no GROQ_API_KEY)" if not api_key else "offline (forced)"
        logger.info("Generating in %s mode…", mode)
        answer = _offline_generate(query, context_str, results)

    # Verify grounding: treat as refusal even if the model appends a trailing
    # "Sources cited: None" block to the refusal sentence.
    if answer.strip().startswith(REFUSAL_STRING):
        return REFUSAL_STRING, []

    cited_sources = _extract_cited_sources(answer, results)
    logger.info("Answer generated. Sources cited: %s", cited_sources)

    return answer, cited_sources


if __name__ == "__main__":
    from chunk import chunk_text
    from embed import embed_and_store
    from retrieve import retrieve

    docs = [
        {"source": "nist_ai_rmf_2026.txt", "text":
         "The NIST AI Risk Management Framework (2026) prescribes three primary metrics "
         "for evaluating generative AI hallucinations: (1) Factual Accuracy Rate — the "
         "proportion of claims in model output that are verifiably grounded in source "
         "documents; (2) Groundedness Score — a semantic similarity measure between "
         "generated claims and retrieved context; (3) Refusal Rate on Out-of-Scope Queries. "
         "Documentation must include model version, test date, dataset hash, and per-metric "
         "score in a structured audit trail."},
    ]

    chunks = chunk_text(docs)
    model, store = embed_and_store(chunks, "gen_test")

    q = "What metrics does NIST prescribe for hallucination testing?"
    result = retrieve(q, model, store)
    answer, sources = generate_answer(q, result)

    print(f"\nQ: {q}")
    print(f"\nA: {answer}")
    print(f"\nCited: {sources}")
