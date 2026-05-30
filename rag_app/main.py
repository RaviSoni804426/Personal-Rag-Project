import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_app import storage
from rag_app.groq_client import embed_texts

load_dotenv()

app = FastAPI()
DB_PATH = os.getenv("DB_PATH", "./data/memories.db")

app.mount("/static", StaticFiles(directory="rag_app/static"), name="static")


@app.get("/")
def root():
    return FileResponse("rag_app/static/index.html")


class ChatRequest(BaseModel):
    message: str
    top_k: int = 5


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message:
        raise HTTPException(status_code=400, detail="message required")

    storage.init_db(DB_PATH)
    q_emb = embed_texts([req.message])[0]
    neighbors = storage.retrieve_similar(DB_PATH, q_emb, top_k=req.top_k)
    context = "\n---\n".join([n["text"] for n in neighbors]) if neighbors else ""

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        prompt = (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{req.message}\n\n"
            "Answer:"
        )
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "prompt": prompt, "max_tokens": 512}
        resp = requests.post("https://api.openai.com/v1/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("text") or data.get("choices", [{}])[0].get("message", {}).get("content")
        return {"answer": text, "retrieved": neighbors}

    return {"answer": None, "retrieved": neighbors, "context": context}


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    storage.init_db(DB_PATH)
    import io

    stored = []
    for f in files:
        content = await f.read()
        name = f.filename
        text = ""
        if name.lower().endswith(".pdf"):
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(io.BytesIO(content))
                pages = [p.extract_text() or "" for p in reader.pages]
                text = "\n".join(pages)
            except Exception:
                text = ""
        elif name.lower().endswith(".docx"):
            try:
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

        embeddings = await run_in_threadpool(embed_texts, [text])
        await run_in_threadpool(storage.add_document, DB_PATH, text, {"source": name}, embeddings[0])
        stored.append(name)

    return {"stored": stored, "count": len(stored)}
