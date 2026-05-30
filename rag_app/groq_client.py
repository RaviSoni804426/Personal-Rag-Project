import os
import requests
import hashlib
from typing import List, Optional
from requests.exceptions import RequestException
import numpy as np

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_EMBEDDING_URL = os.getenv("GROQ_EMBEDDING_URL", "https://api.groq.ai/v1/embeddings")


def _embed_locally(texts: List[str], dim: int = 1536) -> List[List[float]]:
    """Deterministic local embedding fallback when Groq is unavailable.

    Produces normalized vectors of length `dim` based on SHA-256 hashes.
    """
    embeddings = []
    for t in texts:
        digest = hashlib.sha256(t.encode("utf-8")).digest()
        b = digest
        # expand digest deterministically until we have enough bytes
        while len(b) < dim * 4:
            digest = hashlib.sha256(digest).digest()
            b += digest

        arr = np.frombuffer(b, dtype=np.uint32)[:dim].astype(np.float64)
        arr = arr / 0xFFFFFFFF
        arr = arr * 2.0 - 1.0
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        embeddings.append(arr.astype(np.float32).tolist())
    return embeddings


def embed_texts(texts: List[str], api_key: Optional[str] = None, model: str = "embed-1") -> List[List[float]]:
    """Return embeddings for texts.

    Tries Groq if `GROQ_API_KEY` is set; otherwise uses a deterministic local fallback.
    On network errors, falls back to the local embeddings to avoid crashing the app.
    """
    key = api_key or GROQ_API_KEY
    if not key:
        return _embed_locally(texts)

    payload = {"model": model, "input": texts}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(GROQ_EMBEDDING_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except RequestException:
        # don't fail the whole app because embeddings couldn't be fetched
        return _embed_locally(texts)

    embeddings = []
    for item in data.get("data", []):
        emb = item.get("embedding") or item.get("embeddings") or item.get("vector")
        if emb is None:
            return _embed_locally(texts)
        embeddings.append(emb)

    if not embeddings:
        return _embed_locally(texts)

    return embeddings
