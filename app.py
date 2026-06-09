"""
app.py — Gradio Query Interface
The Unofficial Guide RAG Pipeline

Minimal web UI over the end-to-end ask() function in query.py.
Run with: python app.py, then open http://localhost:7860
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

import gradio as gr
from query import ask


def handle_query(question):
    if not question or not question.strip():
        return "Please enter a question.", ""

    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "(no sources — refusal)"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown("# The Unofficial Guide\nAsk a question grounded in the ingested corpus.")
    inp = gr.Textbox(label="Your question")
    btn = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
