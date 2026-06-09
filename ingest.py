"""
Stage 1 — Document Ingestion & Brutal Preprocessing
The Unofficial Guide RAG Pipeline

Loads raw documents from disk (PDF, HTML, plain text, CSV).
Strips boilerplate. Returns clean {"text": str, "source": str} dicts.
"""

import os
import re
import html
import csv
import logging
from pathlib import Path
from typing import Optional

import pdfplumber
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ingest")


# ─── Text Cleaners ────────────────────────────────────────────────────────────

def _clean_text(raw: str) -> str:
    """Strip HTML entities, collapse whitespace, remove control characters."""
    text = html.unescape(raw)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)  # control chars
    text = re.sub(r"\n{3,}", "\n\n", text)   # collapse excessive blank lines
    text = re.sub(r"[ \t]{2,}", " ", text)   # collapse inline whitespace
    return text.strip()


def _strip_html_boilerplate(html_content: str) -> str:
    """
    Extract semantic text from HTML, discarding nav, footer, ads, scripts.
    Retains: article body, section, main, p, h1-h6, blockquote, li.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove noise tags entirely
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe", "figure",
                     "figcaption", "advertisement", "menu"]):
        tag.decompose()

    # Try to isolate main content region
    content_region = (
        soup.find("article") or
        soup.find("main") or
        soup.find(id=re.compile(r"(content|article|body|main)", re.I)) or
        soup.find(class_=re.compile(r"(content|article|body|main)", re.I)) or
        soup.body or
        soup
    )

    # Grab all meaningful text blocks with paragraph boundaries preserved
    paragraphs = []
    for el in content_region.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6",
         "li", "blockquote", "td", "th", "caption"],
        recursive=True,
    ):
        text = el.get_text(separator=" ", strip=True)
        if len(text) > 30:   # discard stub fragments (nav labels, timestamps)
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


# ─── Format-specific loaders ──────────────────────────────────────────────────

def _load_pdf(path: str) -> str:
    """Extract digital text from a PDF using pdfplumber page by page."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text.strip())
            else:
                logger.warning("Page %d in %s returned no text (scanned?)", i + 1, path)

    full_text = "\n\n".join(pages)
    if not full_text.strip():
        raise ValueError(
            f"pdfplumber extracted empty string from '{path}'. "
            "File may be image-only. Route to OCR pipeline or discard."
        )
    return full_text


def _load_html(path: str) -> str:
    """Load an HTML file from disk and strip boilerplate."""
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    return _strip_html_boilerplate(raw)


def _load_txt(path: str) -> str:
    """Load plain text or markdown file."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _load_csv(path: str) -> str:
    """
    Serialize CSV rows as self-contained prose sentences.

    Strategy (from planning.md Challenge 2):
    Each row becomes a complete sentence so that country + value
    never splits across chunk boundaries. Example output:
      "Rwanda's debt-to-GDP ratio was 68.4% in 2024 and 74.8% in 2026
       (a change of +6.4 percentage points). (World Bank Open Data)"
    """
    sentences = []
    source_label = Path(path).stem.replace("_", " ").title()

    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        for row in reader:
            parts = []
            for key in headers:
                val = row.get(key, "").strip()
                if val:
                    parts.append(f"{key}: {val}")
            if parts:
                sentence = "; ".join(parts) + f". ({source_label})"
                sentences.append(sentence)

    if not sentences:
        raise ValueError(f"CSV at '{path}' produced no rows.")
    return "\n\n".join(sentences)


# ─── Public API ───────────────────────────────────────────────────────────────

LOADERS = {
    ".pdf":  _load_pdf,
    ".html": _load_html,
    ".htm":  _load_html,
    ".txt":  _load_txt,
    ".md":   _load_txt,
    ".csv":  _load_csv,
}


def load_and_clean(source_path: str) -> list[dict]:
    """
    Load a single document from disk, clean it, and return a list with
    one dict: {"text": str, "source": str}.

    Raises
    ------
    FileNotFoundError  — path does not exist
    ValueError         — unsupported extension or empty extraction
    """
    path = Path(source_path)

    if not path.exists():
        raise FileNotFoundError(f"Source document not found: '{source_path}'")

    ext = path.suffix.lower()
    loader = LOADERS.get(ext)

    if loader is None:
        raise ValueError(
            f"Unsupported file extension '{ext}' for '{source_path}'. "
            f"Supported: {sorted(LOADERS)}"
        )

    logger.info("Loading %s (%s)", path.name, ext)
    raw_text = loader(str(path))
    clean = _clean_text(raw_text)

    if not clean:
        raise ValueError(
            f"Document '{source_path}' produced empty text after cleaning."
        )

    word_count = len(clean.split())
    logger.info("  ✓ %s — %d words extracted", path.name, word_count)

    return [{"text": clean, "source": path.name}]


def load_corpus(data_dir: str) -> list[dict]:
    """
    Walk a directory and load all supported documents.
    Skips unsupported extensions with a warning.
    Returns a flat list of {"text": str, "source": str} dicts.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Data directory not found: '{data_dir}'")

    docs = []
    skipped = []

    for file_path in sorted(data_path.iterdir()):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in LOADERS:
                try:
                    docs.extend(load_and_clean(str(file_path)))
                except Exception as exc:
                    logger.error("Failed to load '%s': %s", file_path.name, exc)
            else:
                skipped.append(file_path.name)

    if skipped:
        logger.warning("Skipped unsupported files: %s", skipped)

    logger.info("Corpus loaded: %d documents from '%s'", len(docs), data_dir)
    return docs


# ─── Ingestion unit test ──────────────────────────────────────────────────────

def validate_docs(docs: list[dict]) -> None:
    """
    Assert every doc has non-empty 'text' and 'source'.
    Call before handing corpus to the chunking stage.
    Raises AssertionError on the first violation found.
    """
    for i, doc in enumerate(docs):
        assert isinstance(doc.get("text"), str) and doc["text"].strip(), \
            f"Doc[{i}] missing or empty 'text' field. source={doc.get('source')}"
        assert isinstance(doc.get("source"), str) and doc["source"].strip(), \
            f"Doc[{i}] missing or empty 'source' field."
    logger.info("validate_docs: all %d documents passed.", len(docs))


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    docs = load_corpus(path)
    validate_docs(docs)
    for d in docs:
        preview = d["text"][:120].replace("\n", " ")
        print(f"[{d['source']}] {preview}…")
