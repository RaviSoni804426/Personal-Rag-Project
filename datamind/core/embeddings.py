"""
Embeddings service for generating vector representations.
Integrates with Groq API when available and falls back to a local
deterministic embedding model for offline development.
"""

import hashlib
import re
from typing import List, Optional

import numpy as np
import requests

from datamind.config import settings
from datamind.utils import get_logger

logger = get_logger(__name__)


class EmbeddingsService:
    """Service for generating and managing embeddings."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize embeddings service."""
        self.api_key = api_key or settings.GROQ_API_KEY
        self.api_url = api_url or settings.GROQ_EMBEDDING_URL
        self.model = model or settings.EMBEDDING_MODEL
        self.timeout = settings.REQUEST_TIMEOUT
        self.local_mode = not bool(self.api_key)

        if self.local_mode:
            logger.warning(
                "GROQ_API_KEY not configured, using local fallback embeddings"
            )
        else:
            logger.info(f"EmbeddingsService initialized with model: {self.model}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per API call
        
        Returns:
            List of embeddings (same order as input texts)
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")

        if self.local_mode:
            embeddings = [self._embed_locally(text) for text in texts]
            logger.info(f"Successfully generated {len(embeddings)} local embeddings")
            return embeddings

        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self._embed_batch(batch)
            all_embeddings.extend(embeddings)
        
        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def _embed_locally(self, text: str) -> List[float]:
        """Generate a deterministic, normalized fallback embedding locally."""
        dimension = settings.EMBEDDING_DIMENSION
        vector = np.zeros(dimension, dtype=np.float32)
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())

        if not tokens:
            return vector.tolist()

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
        """Send a batch of texts to Groq API."""
        try:
            payload = {
                "model": self.model,
                "input": texts
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
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
            logger.error(f"Groq API request failed: {e}")
            if not self.local_mode:
                logger.warning("Falling back to local embeddings after Groq failure")
                return [self._embed_locally(text) for text in texts]
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
                # Try different possible response formats
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
        """
        Asynchronous embedding generation using thread pool.
        """
        loop = None
        try:
            import asyncio
            loop = asyncio.get_event_loop()
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
