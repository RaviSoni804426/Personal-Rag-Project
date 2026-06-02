"""
Embeddings service for generating vector representations.
Integrates with OpenAI API when available, caches embeddings in SQLite for speed/cost,
and falls back to a local deterministic embedding model for offline development.
"""

import hashlib
import re
import json
import sqlite3
from typing import List, Optional
from pathlib import Path

import numpy as np
import requests

from datamind.config import settings
from datamind.utils import get_logger

logger = get_logger(__name__)


class EmbeddingsService:
    """Service for generating, caching, and managing embeddings."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize embeddings service."""
        # Use OpenAI as primary embeddings provider since Groq doesn't host embeddings
        self.openai_key = api_key or settings.OPENAI_API_KEY
        self.openai_url = api_url or "https://api.openai.com/v1/embeddings"
        self.openai_model = model or "text-embedding-3-small"
        self.timeout = settings.REQUEST_TIMEOUT
        
        # Local mode active if no key is configured
        self.local_mode = not bool(self.openai_key)

        # Ensure database directory exists for the cache
        if settings.DB_PATH:
            Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

        if self.local_mode:
            logger.warning(
                "OPENAI_API_KEY not configured, using local fallback embeddings"
            )
        else:
            logger.info(f"EmbeddingsService initialized with OpenAI model: {self.openai_model}")

    def _get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Query persistent SQLite cache for pre-computed vector."""
        try:
            with sqlite3.connect(settings.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
                    (text_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            # Fail silently since cache tables are created during vectors initialization
            pass
        return None

    def _cache_embedding(self, text_hash: str, embedding: List[float]) -> None:
        """Write computed vector to persistent SQLite cache."""
        try:
            with sqlite3.connect(settings.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_cache (
                        text_hash TEXT PRIMARY KEY,
                        embedding TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute(
                    "INSERT OR REPLACE INTO embedding_cache (text_hash, embedding) VALUES (?, ?)",
                    (text_hash, json.dumps(embedding))
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Failed to save cached embedding: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generate embeddings for multiple texts. Resolves hits via the SQLite cache,
        and requests uncached items in batches to optimize latency and costs.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per API call
        
        Returns:
            List of embeddings (same order as input texts)
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts (batch size: {batch_size})")

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        # Step 1: Query persistent cache
        for idx, text in enumerate(texts):
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cached = self._get_cached_embedding(text_hash)
            if cached is not None:
                results[idx] = cached
            else:
                uncached_indices.append(idx)
                uncached_texts.append(text)

        hit_rate = (len(texts) - len(uncached_indices)) / len(texts) * 100
        logger.info(f"Embedding Cache hits: {len(texts) - len(uncached_indices)}/{len(texts)} ({hit_rate:.1f}%)")

        if not uncached_texts:
            return results  # All items were resolved via cache!

        # Step 2: Fetch embeddings for uncached texts
        computed_embeddings = []
        
        if self.local_mode:
            computed_embeddings = [self._embed_locally(text) for text in uncached_texts]
        else:
            # Process in API batches
            try:
                for i in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[i:i + batch_size]
                    batch_embs = self._embed_batch(batch)
                    computed_embeddings.extend(batch_embs)
            except Exception as e:
                logger.error(f"Batch embedding API request failed: {e}. Falling back to local model.")
                computed_embeddings = [self._embed_locally(text) for text in uncached_texts]

        # Step 3: Cache computed embeddings and reconstruct full results array
        for local_idx, global_idx in enumerate(uncached_indices):
            embedding = computed_embeddings[local_idx]
            results[global_idx] = embedding
            
            # Persist back to database cache
            text = uncached_texts[local_idx]
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._cache_embedding(text_hash, embedding)

        return results

    def _embed_locally(self, text: str) -> List[float]:
        """Generate a deterministic, normalized fallback embedding locally."""
        dimension = settings.EMBEDDING_DIMENSION
        vector = np.zeros(dimension, dtype=np.float32)
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())

        if not tokens:
            return (np.ones(dimension, dtype=np.float32) / np.sqrt(dimension)).tolist()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector.tolist()

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Send a batch of texts to OpenAI API."""
        try:
            payload = {
                "model": self.openai_model,
                "input": texts
            }
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.openai_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            embeddings = self._extract_embeddings(data)
            
            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )
            
            return embeddings
        
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API embedding request failed: {e}")
            raise RuntimeError(f"Embeddings generation failed: {e}") from e
        
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}")
            raise

    @staticmethod
    def _extract_embeddings(response: dict) -> List[List[float]]:
        """Extract embeddings from API response."""
        try:
            embeddings = []
            for item in response.get("data", []):
                emb = (
                    item.get("embedding")
                    or item.get("embeddings")
                    or item.get("vector")
                )
                if emb is None:
                    raise ValueError(f"No embedding found in response item: {item}")
                embeddings.append(emb)
            
            if not embeddings:
                raise ValueError(f"No embeddings in response: {response}")
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to extract embeddings: {e}")
            raise

    def verify_connection(self) -> bool:
        """Verify connection to embeddings service."""
        if self.local_mode:
            return True

        try:
            test_embedding = self.embed_text("test")
            return len(test_embedding) == settings.EMBEDDING_DIMENSION
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """Asynchronous embedding generation using thread pool."""
        import asyncio
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return await loop.run_in_executor(None, self.embed_texts, texts)


# Global embeddings service instance
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get or create embeddings service instance."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service


def initialize_embeddings_service(
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    model: Optional[str] = None
) -> EmbeddingsService:
    """Initialize embeddings service with custom parameters."""
    global _embeddings_service
    _embeddings_service = EmbeddingsService(
        api_key=api_key,
        api_url=api_url,
        model=model
    )
    return _embeddings_service
