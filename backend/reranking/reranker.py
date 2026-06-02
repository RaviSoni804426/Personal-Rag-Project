from typing import List, Dict, Any
from backend.config.config import settings

class CrossEncoderReranker:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.RERANKER_MODEL
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Attempts to load CrossEncoder model locally, with fallback to zero-downtime bypass."""
        try:
            from sentence_transformers import CrossEncoder
            print(f"Loading local CrossEncoder reranking model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            print("CrossEncoder loaded successfully.")
        except Exception as e:
            print(f"Warning: Failed to load local CrossEncoder reranker ({str(e)}). Using RRF scores fallback.")
            self.model = None

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank a list of retrieved chunks against the query.
        Returns the top_n most relevant chunks.
        """
        if not chunks:
            return []
            
        if self.model is None:
            # Fallback bypass: use RRF scores directly and take the top_n elements
            # Since chunks are already sorted by RRF from the HybridRetriever, return top_n
            for idx, c in enumerate(chunks):
                # Map standard confidence scoring based on ranking
                c["rerank_score"] = float(c.get("rrf_score", 1.0 / (idx + 1)))
            return chunks[:top_n]

        try:
            # Prepare query-chunk pairs
            pairs = [[query, c["text_content"]] for c in chunks]
            # Predict scores (higher is better)
            scores = self.model.predict(pairs)
            
            # Inject scores
            for i, score in enumerate(scores):
                chunks[i]["rerank_score"] = float(score)
                
            # Sort by score descending
            chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
            return chunks[:top_n]
        except Exception as e:
            print(f"Error executing CrossEncoder prediction: {e}. Falling back to default rankings.")
            for idx, c in enumerate(chunks):
                c["rerank_score"] = float(c.get("rrf_score", 1.0 / (idx + 1)))
            return chunks[:top_n]
