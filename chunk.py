"""
Stage 2 — Chunking Strategy
The Unofficial Guide RAG Pipeline

Recursive character splitter with paragraph-level semantic boundaries.
Chunk size: 150 tokens (~600 chars). Overlap: 22 tokens (~88 chars).

Built without langchain (network unavailable) — implements the exact same
recursive boundary logic: \\n\\n → \\n → ". " → " "
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("chunk")


# ─── Token approximation ──────────────────────────────────────────────────────
# ~4 characters per token is the standard BPE approximation for English prose.
CHARS_PER_TOKEN = 4


def _tokens_to_chars(tokens: int) -> int:
    return tokens * CHARS_PER_TOKEN


# ─── Recursive character splitter ────────────────────────────────────────────

class RecursiveCharacterSplitter:
    """
    Mimics LangChain's RecursiveCharacterTextSplitter behaviour.

    Splitting hierarchy (tried in order until chunks are small enough):
      1. \\n\\n  — paragraph boundary
      2. \\n    — line break
      3. '. '   — sentence boundary
      4. ' '    — word boundary
      5. ''     — character boundary (last resort)

    Overlap is appended to the END of each chunk so that semantic context
    spanning boundaries is preserved in the following chunk.
    """

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, chunk_size: int, chunk_overlap: int):
        """
        Parameters
        ----------
        chunk_size    : maximum chunk length in characters
        chunk_overlap : overlap in characters appended between consecutive chunks
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text until all pieces fit within chunk_size."""
        if not text.strip():
            return []

        # Find the first separator that actually splits this text
        separator = separators[-1]   # fallback: character-level
        new_separators = []
        for i, sep in enumerate(separators):
            if sep == "" or sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        # Split on the chosen separator
        splits = text.split(separator) if separator else list(text)

        # Rejoin small adjacent pieces; recurse on large pieces
        good_chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split)

            if split_len > self.chunk_size:
                # This single split is too big — recurse with next separator
                if current:
                    merged = separator.join(current)
                    if merged.strip():
                        good_chunks.append(merged)
                    current = []
                    current_len = 0
                if new_separators:
                    sub_chunks = self._split_text(split, new_separators)
                    good_chunks.extend(sub_chunks)
                else:
                    # Force-split at chunk_size
                    for i in range(0, len(split), self.chunk_size):
                        good_chunks.append(split[i : i + self.chunk_size])
                continue

            if current_len + len(separator) + split_len > self.chunk_size and current:
                merged = separator.join(current)
                if merged.strip():
                    good_chunks.append(merged)
                # Apply overlap: keep the tail of current as seed for next chunk
                while current and current_len > self.chunk_overlap:
                    removed = current.pop(0)
                    current_len -= len(removed) + len(separator)
                current_len = max(0, current_len)

            current.append(split)
            current_len += split_len + len(separator)

        if current:
            merged = separator.join(current)
            if merged.strip():
                good_chunks.append(merged)

        return good_chunks

    def split(self, text: str) -> list[str]:
        raw_chunks = self._split_text(text, self.SEPARATORS)
        # Post-process: strip, deduplicate near-empty fragments
        return [c.strip() for c in raw_chunks if len(c.strip()) > 20]


# ─── Public API ───────────────────────────────────────────────────────────────

def chunk_text(
    docs: list[dict],
    chunk_size: int = 150,          # tokens
    overlap: int = 22,              # tokens
    min_chunk_chars: int = 80,      # discard noise fragments shorter than this
) -> list[dict]:
    """
    Split a list of {"text": str, "source": str} dicts into chunks.

    Parameters
    ----------
    docs        : output of ingest.load_corpus()
    chunk_size  : max chunk size in TOKENS (converted to chars internally)
    overlap     : overlap in TOKENS
    min_chunk_chars : minimum character length to keep a chunk

    Returns
    -------
    List of dicts:
        {
            "text":        str,   # chunk text
            "source":      str,   # originating source filename
            "chunk_index": int,   # position within that source document
        }
    """
    chunk_chars   = _tokens_to_chars(chunk_size)
    overlap_chars = _tokens_to_chars(overlap)

    splitter = RecursiveCharacterSplitter(
        chunk_size=chunk_chars,
        chunk_overlap=overlap_chars,
    )

    all_chunks: list[dict] = []

    for doc in docs:
        source = doc["source"]
        text   = doc["text"]

        raw_chunks = splitter.split(text)

        doc_chunks = []
        for idx, chunk_text_str in enumerate(raw_chunks):
            if len(chunk_text_str) < min_chunk_chars:
                logger.debug(
                    "Skipping short fragment (%d chars) from '%s' chunk %d",
                    len(chunk_text_str), source, idx,
                )
                continue
            doc_chunks.append({
                "text":        chunk_text_str,
                "source":      source,
                "chunk_index": idx,
            })

        logger.info(
            "  '%s' → %d chunks (from %d chars)",
            source, len(doc_chunks), len(text),
        )
        all_chunks.extend(doc_chunks)

    total = len(all_chunks)

    # Volume guardrails from planning.md
    if total < 50:
        logger.warning(
            "GUARDRAIL: only %d chunks total. Chunks may be too large. "
            "Consider reducing chunk_size to 150 tokens.", total
        )
    elif total > 2000:
        logger.warning(
            "GUARDRAIL: %d chunks exceeds 2,000. Chunks may be too small "
            "or corpus over-ingested. Consider increasing chunk_size or "
            "pruning source documents.", total
        )

    logger.info("Chunking complete: %d total chunks from %d documents.", total, len(docs))
    return all_chunks


def validate_chunks(chunks: list[dict]) -> None:
    """
    Assert every chunk has required non-empty fields.
    Call before embedding stage to catch metadata pipeline failures early.
    Raises AssertionError on first violation.
    """
    required = {"text", "source", "chunk_index"}
    for i, chunk in enumerate(chunks):
        missing = required - set(chunk.keys())
        assert not missing, f"Chunk[{i}] missing fields: {missing}"
        assert chunk["text"].strip(), f"Chunk[{i}] has empty 'text'. source={chunk['source']}"
        assert chunk["source"].strip(), f"Chunk[{i}] has empty 'source'."
        assert isinstance(chunk["chunk_index"], int), \
            f"Chunk[{i}] 'chunk_index' must be int, got {type(chunk['chunk_index'])}"
    logger.info("validate_chunks: all %d chunks passed.", len(chunks))


if __name__ == "__main__":
    # Quick smoke test
    sample_docs = [
        {
            "source": "test_ap_wire.txt",
            "text": (
                "WASHINGTON — The United States and European Union announced a sweeping new "
                "set of trade regulations in January 2026, targeting digital goods and AI-powered "
                "services. The agreement mandates compliance audits by March 2026.\n\n"
                "Regulators from both sides cited growing concerns about data sovereignty and "
                "algorithmic accountability as primary drivers. Industry groups warned that "
                "compliance timelines are aggressive, with penalties reaching 4% of global revenue "
                "for violations reported after the Q1 deadline.\n\n"
                "Several Sub-Saharan economies joined the accord as observer states, signalling "
                "broader international appetite for harmonised AI trade rules."
            ),
        }
    ]

    chunks = chunk_text(sample_docs, chunk_size=300, overlap=45)
    validate_chunks(chunks)
    print(f"\nProduced {len(chunks)} chunks:\n")
    for c in chunks:
        print(f"  [{c['source']} | chunk {c['chunk_index']}] "
              f"({len(c['text'])} chars): {c['text'][:80]}…")
