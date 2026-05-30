import os
from typing import List

import gradio as gr
from dotenv import load_dotenv

from rag_app import storage
from rag_app.groq_client import embed_texts

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./data/memories.db")

storage.init_db(DB_PATH)


def ingest_files(files: List[gr.File]):
    stored = []
    for f in files or []:
        path = f.name
        with open(path, "rb") as fh:
            content = fh.read()
        text = ""
        if path.lower().endswith(".pdf"):
            try:
                import io
                from PyPDF2 import PdfReader

                reader = PdfReader(io.BytesIO(content))
                pages = [p.extract_text() or "" for p in reader.pages]
                text = "\n".join(pages)
            except Exception:
                text = ""
        elif path.lower().endswith(".docx"):
            try:
                import io
                import docx

                doc = docx.Document(io.BytesIO(content))
                paragraphs = [p.text for p in doc.paragraphs]
                text = "\n".join(paragraphs)
            except Exception:
                text = ""
        else:
            try:
                text = content.decode("utf-8")
            except Exception:
                text = ""

        if not text.strip():
            continue

        emb = embed_texts([text])[0]
        storage.add_document(DB_PATH, text, {"source": path}, emb)
        stored.append(os.path.basename(path))

    return f"Stored {len(stored)} files: {', '.join(stored)}"


def answer(query: str, top_k: int = 5):
    if not query:
        return ""
    q_emb = embed_texts([query])[0]
    neighbors = storage.retrieve_similar(DB_PATH, q_emb, top_k=top_k)
    context = "\n---\n".join([n["text"] for n in neighbors])
    return context


with gr.Blocks() as demo:
    gr.Markdown("# Personal RAG Assistant (Groq)\nUpload documents and ask questions.")
    with gr.Row():
        with gr.Column(scale=1):
            files = gr.File(file_count="multiple", label="Upload files (pdf, docx, txt)")
            ingest_btn = gr.Button("Ingest files")
            status = gr.Textbox(label="Ingest status")
        with gr.Column(scale=2):
            query = gr.Textbox(label="Question")
            top_k = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="top_k")
            ask = gr.Button("Ask")
            answer_box = gr.Textbox(label="Answer", lines=10)

    ingest_btn.click(fn=ingest_files, inputs=[files], outputs=[status])
    ask.click(fn=answer, inputs=[query, top_k], outputs=[answer_box])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))
