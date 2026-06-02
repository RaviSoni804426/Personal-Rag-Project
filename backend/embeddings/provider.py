import hashlib
import json
from typing import List, Dict, Any
import numpy as np
from sqlalchemy.orm import Session
from backend.config.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import EmbeddingCache

class EmbeddingProvider:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initializes SentenceTransformer, fallback to basic term frequency if failed."""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading local SentenceTransformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Warning: Failed to load local SentenceTransformer model ({str(e)}). Using robust lightweight mock vectorizer.")
            self.model = None

    def _generate_mock_vector(self, text: str, dimension: int = 384) -> List[float]:
        """Highly robust fallback hashing vectorizer to ensure 100% uptime."""
        # Simple word frequency vectorizer + hash deterministic mapping
        words = text.lower().split()
        vector = np.zeros(dimension)
        
        # Seed generator deterministically
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % dimension
            vector[idx] += 1.0
            
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of strings. Checks SQLite/Postgres persistent cache first
        to bypass neural net computation for duplicate chunks.
        """
        if not texts:
            return []

        db: Session = SessionLocal()
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        # 1. Check persistent caching first
        try:
            for idx, text in enumerate(texts):
                text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                cached_item = db.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
                
                if cached_item:
                    results[idx] = json.loads(cached_item.embedding_json)
                else:
                    uncached_indices.append(idx)
                    uncached_texts.append(text)
        except Exception as e:
            print(f"Embedding cache read failure: {e}")
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts
            
        # 2. Compute vectors for cache misses
        if uncached_texts:
            computed_vectors = []
            if self.model is not None:
                try:
                    # Batch model embedding
                    embeddings = self.model.encode(uncached_texts, show_progress_bar=False)
                    computed_vectors = [v.tolist() for v in embeddings]
                except Exception as e:
                    print(f"Model generation error, falling back to lightweight vectors: {e}")
                    dimension = 384 if "mini" in self.model_name.lower() else 1024
                    computed_vectors = [self._generate_mock_vector(txt, dimension) for txt in uncached_texts]
            else:
                dimension = 1024 if "large" in self.model_name.lower() else 384
                computed_vectors = [self._generate_mock_vector(txt, dimension) for txt in uncached_texts]
                
            # 3. Store new embeddings in cache and results array
            try:
                for idx, text, vector in zip(uncached_indices, uncached_texts, computed_vectors):
                    results[idx] = vector
                    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    
                    # Store in database
                    cache_item = EmbeddingCache(
                        text_hash=text_hash,
                        embedding_json=json.dumps(vector)
                    )
                    db.merge(cache_item)
                db.commit()
            except Exception as e:
                print(f"Embedding cache write failure: {e}")
                db.rollback()
                
        db.close()
        return results

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string."""
        return self.embed_texts([query])[0]
