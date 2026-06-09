"""
query.py — End-to-End Query Interface
The Unofficial Guide RAG Pipeline

Builds the pipeline once at import time and exposes a single `ask()`
function that runs Stages 4-5 (retrieve + generate) for a user question.
This is the function the Gradio UI (app.py) calls.
"""

import logging

from dotenv import load_dotenv
load_dotenv()

from pipeline import build_pipeline
from retrieve import retrieve
from generate import generate_answer

logger = logging.getLogger("query")

_model = None
_store = None


def _get_pipeline():
    """Lazily build (or reuse) the embedding model + vector store."""
    global _model, _store
    if _model is None or _store is None:
        _model, _store = build_pipeline()
    return _model, _store


def ask(question: str) -> dict:
    """
    Run a user question through retrieval + grounded generation.

    Returns
    -------
    dict:
        "answer"  : str  — the grounded answer (or the refusal string)
        "sources" : list[str] — source documents the answer was grounded in
    """
    model, store = _get_pipeline()

    retrieval = retrieve(question, model, store)
    answer, sources = generate_answer(question, retrieval)

    return {"answer": answer, "sources": sources}
