"""
Evaluation Harness — The Unofficial Guide RAG Pipeline
planning.md §Evaluation Plan

Loops through all 5 test questions, runs the full pipeline for each,
displays retrieved chunks with distance scores, displays the LLM answer,
and prompts the user for a verdict. Logs results to evaluation_log.csv.

Verdict options:
  A  = Accurate
  P  = Partially Accurate
  I  = Inaccurate
  R  = Correct Refusal
  S  = Skip (for automated runs)
"""

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from embed import EmbeddingModel, VectorStore, DISTANCE_THRESHOLD
from retrieve import retrieve
from generate import generate_answer, REFUSAL_STRING

logger = logging.getLogger("evaluate")

# ─── The 5 evaluation questions ──────────────────────────────────────────────

TEST_QUESTIONS = [
    {
        "id": "Q1",
        "category": "Cross-domain synthesis",
        "question": (
            "According to the 2026 UNESCO Institute for Statistics release, what is the "
            "current global percentage of GDP allocated to R&D, and how does this statistical "
            "trend align with public trust sentiments on technological innovation from the "
            "Pew Research Center?"
        ),
        "expected_criteria": (
            "States the specific UNESCO R&D GDP percentage (2.63%) from the 2026 release. "
            "References Pew trust data (direction: declining — 54% distrust). "
            "Both claims cite respective source documents. No causal extrapolation."
        ),
        "expected_refusal": False,
    },
    {
        "id": "Q2",
        "category": "Contradictory information resolution",
        "question": (
            "Compare early arXiv findings on room-temperature superconductivity (2026 preprints) "
            "with the peer-reviewed PubMed Central consensus on the same materials' human "
            "toxicity. How do their conclusions differ?"
        ),
        "expected_criteria": (
            "Identifies arXiv's preliminary superconductivity claims. References PMC's "
            "peer-reviewed findings on rare earth hydride toxicity (insufficient safe exposure "
            "limits, IARC Group 2B). Names both source documents. Does not resolve the "
            "scientific dispute beyond what the texts state."
        ),
        "expected_refusal": False,
    },
    {
        "id": "Q3",
        "category": "Technical framework application",
        "question": (
            "What specific metrics does the NIST AI Risk Management Framework prescribe for "
            "evaluating generative AI hallucinations, and how should an organization document "
            "these tests?"
        ),
        "expected_criteria": (
            "Lists FAR (Factual Accuracy Rate), GS (Groundedness Score), RROSQ (Refusal Rate "
            "on Out-of-Scope Queries). Describes required audit trail fields: system ID, "
            "dataset hash, date, evaluator, per-metric scores, delta scores. Answer fully "
            "bounded to NIST chunks — no external AI safety knowledge injected."
        ),
        "expected_refusal": False,
    },
    {
        "id": "Q4",
        "category": "Regional economic trend extraction",
        "question": (
            "Based on World Bank Open Data, which Sub-Saharan African countries showed a "
            "debt-to-GDP ratio increase exceeding 5% between 2024 and 2026, and what "
            "macroeconomic drivers did The Guardian attribute to this shift?"
        ),
        "expected_criteria": (
            "Names countries with >5pp increase: Zambia (+12.8), Ethiopia (+8.6), Ghana (+8.2), "
            "Kenya (+7.5), Tanzania (+5.8), Rwanda (+6.4), Nigeria (+5.4) from World Bank data. "
            "References Guardian's macroeconomic drivers: rising interest rates, weak tax "
            "collection, climate-related fiscal stress, dollar strength."
        ),
        "expected_refusal": False,
    },
    {
        "id": "Q5",
        "category": "Out-of-scope refusal (adversarial)",
        "question": "What were the top five AI product launches announced at CES 2026?",
        "expected_criteria": (
            "System returns EXACTLY: 'I do not have enough information to answer this question.' "
            "Any hallucinated product name is a CRITICAL FAILURE. "
            "This proves the grounding constraints are working."
        ),
        "expected_refusal": True,
    },
]

# ─── Verdict system ───────────────────────────────────────────────────────────

VERDICTS = {
    "A": "Accurate",
    "P": "Partially Accurate",
    "I": "Inaccurate",
    "R": "Correct Refusal",
    "S": "Skipped",
}

VERDICT_COLOURS = {
    "A": "\033[92m",   # green
    "P": "\033[93m",   # yellow
    "I": "\033[91m",   # red
    "R": "\033[92m",   # green
    "S": "\033[90m",   # grey
}
RESET = "\033[0m"


def _colour(text: str, code: str) -> str:
    if sys.stdout.isatty():
        return f"{code}{text}{RESET}"
    return text


def _divider(char="─", width=72):
    print(char * width)


# ─── Individual question runner ───────────────────────────────────────────────

def run_question(
    test: dict,
    model: EmbeddingModel,
    store: VectorStore,
    auto_mode: bool = False,
) -> dict:
    """Run a single evaluation question through the full pipeline."""

    _divider("═")
    print(f"\n{_colour(test['id'], VERDICT_COLOURS['A'])} — {test['category']}")
    print(f"\nQuestion:\n  {test['question']}\n")
    print(f"Expected criteria:\n  {test['expected_criteria']}\n")
    if test["expected_refusal"]:
        print(_colour("  ⚠ This question SHOULD produce a refusal response.", "\033[93m"))
    _divider()

    # ── Retrieval ──
    retrieval_result = retrieve(test["question"], model, store)

    print("\n📦 Retrieved chunks:")
    if not retrieval_result["results"]:
        print("  (no chunks returned)")
    for r in retrieval_result["results"]:
        dist_colour = "\033[92m" if r["distance"] < 0.4 else \
                      "\033[93m" if r["distance"] < DISTANCE_THRESHOLD else "\033[91m"
        dist_str = f"{r['distance']:.3f}"
        print(
            f"\n  rank={r['rank']} | "
            f"dist={_colour(dist_str, dist_colour)} | "
            f"source={r['source_document']} | "
            f"chunk_idx={r['chunk_index']}"
        )
        preview = r["raw_text_payload"][:200].replace("\n", " ")
        print(f"  ↳ {preview}…")

    if retrieval_result["all_below_threshold"]:
        print(_colour(
            f"\n  ⚠ Quality gate: all chunks have distance > {DISTANCE_THRESHOLD}. "
            "Refusal will be triggered.", "\033[91m"
        ))

    # ── Generation ──
    print("\n🤖 Generated answer:")
    answer, cited_sources = generate_answer(test["question"], retrieval_result)
    print()
    print(answer)

    if cited_sources:
        print(f"\n  📎 Cited sources: {cited_sources}")

    # ── Refusal check ──
    is_refusal = (answer.strip() == REFUSAL_STRING.strip())
    if test["expected_refusal"]:
        if is_refusal:
            print(_colour("\n  ✓ Correct refusal — grounding constraints working.", "\033[92m"))
        else:
            print(_colour("\n  ✗ CRITICAL FAILURE — expected refusal but got an answer!", "\033[91m"))
    else:
        if is_refusal:
            print(_colour("\n  ⚠ Unexpected refusal — retrieval may have failed.", "\033[93m"))

    # ── Verdict ──
    if auto_mode:
        if test["expected_refusal"] and is_refusal:
            verdict_key = "R"
        elif test["expected_refusal"] and not is_refusal:
            verdict_key = "I"
        else:
            verdict_key = "S"
    else:
        print("\n┌─────────────────────────────────────┐")
        print("│ Verdict: A)ccurate  P)artial  I)naccurate  R)efusal  S)kip │")
        print("└─────────────────────────────────────┘")
        raw = input("  Your verdict → ").strip().upper()
        verdict_key = raw if raw in VERDICTS else "S"

    verdict_label = VERDICTS[verdict_key]
    v_colour = VERDICT_COLOURS.get(verdict_key, "\033[0m")
    print(f"\n  Verdict recorded: {_colour(verdict_label, v_colour)}\n")

    return {
        "question_id":      test["id"],
        "category":         test["category"],
        "question":         test["question"],
        "expected_refusal": test["expected_refusal"],
        "num_results":      len(retrieval_result["results"]),
        "best_distance":    retrieval_result["results"][0]["distance"] if retrieval_result["results"] else 1.0,
        "sources_retrieved": ", ".join(r["source_document"] for r in retrieval_result["results"]),
        "answer_excerpt":   answer[:300].replace("\n", " "),
        "cited_sources":    ", ".join(cited_sources),
        "is_refusal":       is_refusal,
        "expected_refusal_met": (test["expected_refusal"] == is_refusal),
        "verdict":          verdict_label,
        "verdict_key":      verdict_key,
    }


# ─── CSV logger ───────────────────────────────────────────────────────────────

def save_results(results: list[dict], log_dir: str = "logs") -> str:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(log_dir) / f"evaluation_{timestamp}.csv"

    if not results:
        return str(path)

    fieldnames = list(results[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return str(path)


# ─── Summary printer ─────────────────────────────────────────────────────────

def print_summary(results: list[dict]) -> None:
    _divider("═")
    print("\n📊 EVALUATION SUMMARY\n")

    counts = {v: 0 for v in VERDICTS.values()}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    for key, label in VERDICTS.items():
        c = counts.get(label, 0)
        bar = "█" * c
        colour = VERDICT_COLOURS.get(key, "")
        label_padded = f"{label:<22}"
        print(f"  {_colour(label_padded, colour)} {bar} {c}")

    print()
    refusal_tests = [r for r in results if r["expected_refusal"]]
    refusals_ok   = sum(1 for r in refusal_tests if r["expected_refusal_met"])
    print(f"  Refusal accuracy: {refusals_ok}/{len(refusal_tests)} out-of-scope queries correctly refused")

    avg_dist = sum(r["best_distance"] for r in results) / len(results) if results else 0
    print(f"  Mean best-chunk distance: {avg_dist:.3f}")
    _divider()


# ─── Main entry point ─────────────────────────────────────────────────────────

def main(auto_mode: bool = False):
    """Run the full evaluation suite."""

    logging.basicConfig(
        level=logging.WARNING,    # Suppress info noise during eval
        format="%(asctime)s [%(levelname)s] — %(message)s",
    )

    print("\n" + "═" * 72)
    print("  THE UNOFFICIAL GUIDE — RAG EVALUATION HARNESS")
    print("═" * 72 + "\n")

    # ── Load pre-built pipeline ──
    vectorstore_dir = "vectorstore"
    collection_name = "unofficial_guide"
    db_path    = f"{vectorstore_dir}/{collection_name}.db"
    chroma_dir = Path(vectorstore_dir) / "chroma"

    if not chroma_dir.exists():
        print("  ⚠ Pipeline not found. Run: python pipeline.py  first.\n")
        sys.exit(1)

    model = EmbeddingModel()
    store = VectorStore(db_path)
    print(f"  Loaded vector store: {store.count()} chunks indexed.\n")

    results = []
    for test in TEST_QUESTIONS:
        result = run_question(test, model, store, auto_mode=auto_mode)
        results.append(result)

    print_summary(results)
    log_path = save_results(results)
    print(f"\n  Results saved to: {log_path}\n")

    return results


if __name__ == "__main__":
    auto = "--auto" in sys.argv or "-a" in sys.argv
    main(auto_mode=auto)
