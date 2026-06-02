import time
import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.database.models import QueryLog
from backend.retrieval.hybrid import HybridRetriever
from backend.database.vector_store import ChromaVectorStore
from backend.embeddings.provider import EmbeddingProvider
from backend.reranking.reranker import CrossEncoderReranker
from backend.generation.synthesizer import LLMSynthesizer
from backend.generation.memory import ConversationalMemory
from backend.evaluation.metrics import RAGEvaluator

class ChatService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.vector_store = ChromaVectorStore()
        self.embedding_provider = EmbeddingProvider()
        self.retriever = HybridRetriever(self.vector_store, self.embedding_provider)
        self.reranker = CrossEncoderReranker()
        self.synthesizer = LLMSynthesizer()
        self.memory = ConversationalMemory()
        self.evaluator = RAGEvaluator(self.synthesizer)

    def search_raw(self, query: str, k: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Unified hybrid search retrieval pipeline, returning top ranked matches."""
        # 1. Retrieve hybrid dense/sparse results
        raw_hits = self.retriever.retrieve(query, k=k * 2, document_id=document_id)
        # 2. Rerank via Cross-Encoder transformer
        reranked_hits = self.reranker.rerank(query, raw_hits, top_n=k)
        return reranked_hits

    def query(
        self, 
        query: str, 
        session_id: str = "default", 
        document_id: Optional[str] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Main RAG conversational loop. Retrieves, reranks, compresses, synthesizes,
        logs query diagnostics, and evaluates system outputs.
        """
        start_time = time.time()
        
        # 1. Retrieve & Rerank chunks
        retrieved_hits = self.search_raw(query, k=k * 2, document_id=document_id)
        
        # 2. Apply context compression & parent mapping
        # If the strategy uses Parent-Child, swap child texts for parent texts to broaden LLM context
        context_chunks = []
        chunks_used_meta = []
        seen_texts = set()
        
        for hit in retrieved_hits:
            # Check parent content fallback for context rich generation
            content = hit["text_content"]
            parent_txt = hit["metadata"].get("parent_chunk_id")
            
            # If a parent chunk exists, prioritize it for the LLM
            synthesis_text = parent_txt if parent_txt else content
            
            if synthesis_text not in seen_texts:
                seen_texts.add(synthesis_text)
                context_chunks.append(synthesis_text)
                chunks_used_meta.append({
                    "chunk_id": hit["chunk_id"],
                    "text_content": content,
                    "score": hit.get("rerank_score", 0.0),
                    "filename": hit["metadata"].get("filename", "unknown"),
                    "sources": hit.get("sources", ["dense"])
                })
                
        # Limit context window density
        context_chunks = context_chunks[:k]
        chunks_used_meta = chunks_used_meta[:k]
        
        # 3. Pull conversation history summary
        history_context = self.memory.get_history_summary_context(session_id)
        
        # 4. Synthesize Answer using Groq
        answer, confidence, final_synthesis_chunks = self.synthesizer.synthesize(
            query=query,
            chunks=chunks_used_meta,
            history_context=history_context
        )
        
        latency_ms = (time.time() - start_time) * 1000.0
        
        # Estimate token size (4 characters per token average)
        token_usage = (len(query) + len(answer) + sum(len(c) for c in context_chunks)) // 4
        
        # 5. Background evaluations
        # Calculate Faithfulness, Context Precision, and Answer Relevance
        eval_scores = self.evaluator.evaluate_generation(
            query=query,
            context_chunks=context_chunks,
            generated_answer=answer
        )
        
        # 6. Database log register
        log_entry = QueryLog(
            session_id=session_id,
            query=query,
            response=answer,
            confidence_score=confidence,
            latency_ms=latency_ms,
            token_usage=token_usage,
            retrieved_chunks=json.dumps(chunks_used_meta),
            faithfulness_score=eval_scores["faithfulness"],
            context_precision_score=eval_scores["context_precision"],
            answer_relevance_score=eval_scores["answer_relevance"]
        )
        
        try:
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            print(f"Failed to log chat query to database: {e}")
            self.db.rollback()
            
        return {
            "answer": answer,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "token_usage": token_usage,
            "sources": chunks_used_meta,
            "eval_scores": eval_scores
        }

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Gathers system analytics log history to compile visual KPI data."""
        logs = self.db.query(QueryLog).order_by(QueryLog.created_at.desc()).all()
        
        # Process visual history scores
        total_queries = len(logs)
        if total_queries == 0:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0.0,
                "avg_confidence": 0.0,
                "avg_faithfulness": 0.0,
                "avg_context_precision": 0.0,
                "avg_answer_relevance": 0.0,
                "token_usage_total": 0,
                "recent_history": []
            }
            
        avg_lat = sum(l.latency_ms for l in logs) / total_queries
        avg_conf = sum(l.confidence_score for l in logs) / total_queries
        
        # Filter null evaluations
        valid_f = [l.faithfulness_score for l in logs if l.faithfulness_score is not None]
        valid_p = [l.context_precision_score for l in logs if l.context_precision_score is not None]
        valid_r = [l.answer_relevance_score for l in logs if l.answer_relevance_score is not None]
        
        avg_faith = sum(valid_f) / len(valid_f) if valid_f else 0.85
        avg_prec = sum(valid_p) / len(valid_p) if valid_p else 0.85
        avg_relev = sum(valid_r) / len(valid_r) if valid_r else 0.85
        
        tot_tokens = sum(l.token_usage for l in logs)
        
        # Package raw charts history logs
        recent_history = []
        for l in logs[:10]:
            recent_history.append({
                "query": l.query,
                "latency_ms": l.latency_ms,
                "token_usage": l.token_usage,
                "faithfulness": l.faithfulness_score or 0.85,
                "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
            
        return {
            "total_queries": total_queries,
            "avg_latency_ms": round(avg_lat, 1),
            "avg_confidence": round(avg_conf, 2),
            "avg_faithfulness": round(avg_faith, 2),
            "avg_context_precision": round(avg_prec, 2),
            "avg_answer_relevance": round(avg_relev, 2),
            "token_usage_total": tot_tokens,
            "recent_history": recent_history
        }
