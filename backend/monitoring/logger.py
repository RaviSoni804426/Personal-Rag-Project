import logging
import time
from typing import Dict, Any, List, Optional
from backend.config.config import settings

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("enterprise_rag_platform")

class LangSmithTracer:
    def __init__(self):
        self.tracing_enabled = settings.LANGCHAIN_TRACING_V2.lower() == "true"
        self.api_key = settings.LANGCHAIN_API_KEY
        self.project = settings.LANGCHAIN_PROJECT
        self._initialize_tracing()

    def _initialize_tracing(self):
        if self.tracing_enabled and self.api_key:
            try:
                # Set env variables so LangChain client automatically intercepts runs
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = self.api_key
                os.environ["LANGCHAIN_PROJECT"] = self.project
                logger.info("LangSmith Tracing compatible environment hooks initialized.")
            except Exception as e:
                logger.warning(f"Failed to bind LangSmith environment hooks: {e}")

    def trace_retrieval(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Logs retrieval execution metadata."""
        trace = {
            "query": query,
            "chunks_count": len(retrieved_chunks),
            "timestamp": time.time()
        }
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks for query: '{query[:50]}...'")
        return trace

    def trace_generation(
        self, 
        query: str, 
        response: str, 
        latency_ms: float, 
        tokens: int,
        confidence: float
    ):
        """Logs generation execution metadata."""
        logger.info(
            f"Query: '{query[:50]}...' completed in {latency_ms:.1f}ms | "
            f"Tokens: {tokens} | Confidence: {confidence:.2f}"
        )

# Global instances
system_logger = logger
tracer = LangSmithTracer()
