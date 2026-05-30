import os
import requests
from typing import List, Optional
from requests.exceptions import RequestException

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_EMBEDDING_URL = os.getenv("GROQ_EMBEDDING_URL", "https://api.groq.ai/v1/embeddings")


def embed_texts(texts: List[str], api_key: Optional[str] = None, model: str = "embed-1") -> List[List[float]]:
    """Send texts to Groq embeddings endpoint and return embeddings.

    This function is strict Groq-only mode: any network or API error raises.
    """
    key = api_key or GROQ_API_KEY
    if not key:
        raise ValueError("GROQ_API_KEY not set")

    payload = {"model": model, "input": texts}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(GROQ_EMBEDDING_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except RequestException as e:
        raise RuntimeError(f"Groq embedding request failed: {e}") from e

    embeddings = []
    for item in data.get("data", []):
        emb = item.get("embedding") or item.get("embeddings") or item.get("vector")
        if emb is None:
            raise RuntimeError(f"Unexpected response format from Groq embeddings: {data}")
        embeddings.append(emb)

    if not embeddings:
        raise RuntimeError(f"Groq embeddings response did not contain vectors: {data}")

    return embeddings
