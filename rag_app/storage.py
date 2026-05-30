import json
import os
import sqlite3
from typing import List, Optional, Tuple

import numpy as np


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            metadata TEXT,
            embedding TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_document(db_path: str, text: str, metadata: Optional[dict], embedding: List[float]):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (text, metadata, embedding) VALUES (?, ?, ?)",
        (text, json.dumps(metadata or {}), json.dumps(embedding)),
    )
    conn.commit()
    conn.close()


def all_embeddings(db_path: str) -> List[Tuple[int, str, dict, List[float]]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, text, metadata, embedding FROM memories")
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        mid, text, meta_s, emb_s = r
        meta = json.loads(meta_s or "{}")
        emb = json.loads(emb_s)
        result.append((mid, text, meta, emb))
    return result


def retrieve_similar(db_path: str, query_embedding: List[float], top_k: int = 5):
    items = all_embeddings(db_path)
    if not items:
        return []
    embs = np.array([i[3] for i in items], dtype=np.float32)
    q = np.array(query_embedding, dtype=np.float32)

    dots = embs @ q
    embs_norm = np.linalg.norm(embs, axis=1)
    q_norm = np.linalg.norm(q)
    sims = dots / (embs_norm * q_norm + 1e-8)
    idx = np.argsort(-sims)[:top_k]
    results = []
    for i in idx:
        mid, text, meta, _emb = items[i]
        results.append({"id": mid, "text": text, "metadata": meta, "score": float(sims[i])})
    return results
