import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from backend.database.connection import SessionLocal
from backend.database.models import DocumentChunk
from backend.database.vector_store import ChromaVectorStore
from backend.embeddings.provider import EmbeddingProvider

class HybridRetriever:
    def __init__(self, vector_store: ChromaVectorStore, embedding_provider: EmbeddingProvider):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer removing punctuation and lowering strings."""
        if not text:
            return []
        text_clean = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in text_clean.split() if w.strip()]

    def _get_sparse_scores(self, query: str, chunks: List[DocumentChunk], k: int = 10) -> List[Dict[str, Any]]:
        """Performs BM25 keyword matching across indexed chunks."""
        if not chunks:
            return []
            
        tokenized_corpus = [self._tokenize(chunk.text_content) for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = self._tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        # Zip, score, and rank
        scored_chunks = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only include hits with keyword overlap
                chunk = chunks[idx]
                scored_chunks.append({
                    "chunk_id": chunk.id,
                    "text_content": chunk.text_content,
                    "score": float(score),
                    "metadata": {
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index
                    }
                })
                
        # Sort descending
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:k]

    def retrieve(self, query: str, k: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes hybrid dense vector and sparse keyword search, fusing rankings
        via Reciprocal Rank Fusion (RRF).
        """
        # 1. Fetch dense results
        query_vector = self.embedding_provider.embed_query(query)
        dense_hits = self.vector_store.search(query_vector, k=k * 2, document_id=document_id)
        
        # 2. Fetch sparse (BM25) results from matching database chunks
        db = SessionLocal()
        try:
            db_query = db.query(DocumentChunk)
            if document_id:
                db_query = db_query.filter(DocumentChunk.document_id == document_id)
            chunks = db_query.all()
        except Exception as e:
            print(f"Error fetching chunks from DB for BM25: {e}")
            chunks = []
        finally:
            db.close()
            
        sparse_hits = self._get_sparse_scores(query, chunks, k=k * 2)
        
        # 3. Reciprocal Rank Fusion (RRF)
        # RRF(d) = sum(1 / (60 + rank(d)))
        rrf_scores = {}
        rrf_constant = 60
        
        # Score dense ranks
        for rank, hit in enumerate(dense_hits):
            cid = hit["chunk_id"]
            if cid not in rrf_scores:
                rrf_scores[cid] = {"hit": hit, "rrf_score": 0.0, "sources": []}
            rrf_scores[cid]["rrf_score"] += 1.0 / (rrf_constant + rank + 1)
            rrf_scores[cid]["sources"].append("dense")
            
        # Score sparse ranks
        for rank, hit in enumerate(sparse_hits):
            cid = hit["chunk_id"]
            if cid not in rrf_scores:
                # Need to convert metadata structure slightly to match vector store standard
                rrf_scores[cid] = {"hit": hit, "rrf_score": 0.0, "sources": []}
            rrf_scores[cid]["rrf_score"] += 1.0 / (rrf_constant + rank + 1)
            rrf_scores[cid]["sources"].append("sparse")
            
        # Compile and sort combined rankings
        fused_results = []
        for cid, info in rrf_scores.items():
            hit_data = info["hit"]
            hit_data["rrf_score"] = info["rrf_score"]
            hit_data["sources"] = info["sources"]
            # Convert raw score index
            fused_results.append(hit_data)
            
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:k]
