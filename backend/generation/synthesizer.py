import re
import json
import time
from typing import List, Dict, Any, Tuple
from groq import Groq
from backend.config.config import settings

class LLMSynthesizer:
    def __init__(self, provider: str = "groq"):
        self.provider = provider.lower().strip()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the active LLM client based on configuration."""
        if self.provider == "groq" and settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                print("Groq LLM Client initialized successfully.")
            except Exception as e:
                print(f"Warning: Failed to initialize Groq client: {e}. Attempting failover to OpenAI.")
                self._initialize_openai()
        else:
            self._initialize_openai()

    def _initialize_openai(self):
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.provider = "openai"
                print("OpenAI LLM Client initialized successfully as failover.")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}. RAG Synthesizer entering API-free mode.")
                self.client = None
        else:
            print("Note: No operational LLM keys detected. Synthesizer entering offline fallback mode.")
            self.client = None

    def _offline_synthesize_fallback(self, query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, float]:
        """Highly robust offline analyzer mapping matches directly when API keys are missing or exhausted."""
        # Simple local extractor searching for matching keyword density
        query_words = set(query.lower().split())
        best_match = None
        highest_overlap = 0
        
        for c in chunks:
            words = set(c["text_content"].lower().split())
            overlap = len(query_words.intersection(words))
            if overlap > highest_overlap:
                highest_overlap = overlap
                best_match = c
                
        if best_match and highest_overlap > 1:
            fn = best_match["metadata"].get("filename", "document")
            ans = f"**[Offline Local Extract]** Based on **{fn}**:\n\n\"{best_match['text_content']}\"\n\n*(Note: LLM API key is unconfigured. Showing exact vector-matched context block.)*"
            return ans, 0.75
            
        return "I could not find sufficient information in the uploaded documents.", 0.0

    def synthesize(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        history_context: str = ""
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Synthesizes an answer using the retrieved chunks.
        Returns:
            Tuple[answer_text, confidence_score, chunks_used]
        """
        if not chunks:
            return "I could not find sufficient information in the uploaded documents.", 0.0, []

        # Remove duplicates
        seen_texts = set()
        unique_chunks = []
        for c in chunks:
            cleaned_text = c["text_content"].strip()
            if cleaned_text not in seen_texts:
                seen_texts.add(cleaned_text)
                unique_chunks.append(c)
                
        # Limit to top 5 for synthesis to keep context compressed and focused
        synthesis_chunks = unique_chunks[:5]
        
        # Build context prompt
        context_str = ""
        for i, c in enumerate(synthesis_chunks):
            filename = c["metadata"].get("filename", "unknown_doc")
            context_str += f"[Document {i+1} | Source: {filename}]\n{c['text_content']}\n\n"

        system_prompt = (
            "You are a Principal AI Analyst. Analyze the retrieved documents and answer the user query based ONLY on the provided context.\n"
            "Rules:\n"
            "1. Base your answer strictly on the provided documents. If the context does not contain sufficient details to answer, output EXACTLY: "
            "\"I could not find sufficient information in the uploaded documents.\" and nothing else.\n"
            "2. Never make up facts or extrapolate. Do not hallucinate.\n"
            "3. Cite sources! For every assertion you make, append its document reference, e.g., '[source: filename.pdf]'.\n"
            "4. Provide a confidence rating (0.0 to 1.0) measuring how completely the retrieved document context satisfies the query.\n"
            "5. You MUST include your confidence score at the very end of your response inside a valid JSON object in a single line, "
            "formatted exactly like this: {\"confidence_rating\": 0.95}"
        )

        user_content = (
            f"{history_context}\n"
            f"Retrieved Document Context:\n{context_str}\n"
            f"User Query: {query}\n\n"
            f"Answer:"
        )

        if self.client is None:
            ans, conf = self._offline_synthesize_fallback(query, synthesis_chunks)
            return ans, conf, synthesis_chunks

        # Execute completion based on active provider
        try:
            model = settings.GROQ_DEFAULT_MODEL if self.provider == "groq" else "gpt-3.5-turbo"
            
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS
                )
            else:
                # OpenAI model call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS
                )
                
            raw_answer = response.choices[0].message.content.strip()
            
            # Extract confidence rating
            confidence = 0.85  # default
            confidence_match = re.search(r"\{\s*\"confidence_rating\"\s*:\s*([0-9\.]+)\s*\}", raw_answer)
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1))
                    # Remove the JSON line from the final answer text
                    raw_answer = re.sub(r"\n*\{\s*\"confidence_rating\"\s*:\s*[0-9\.]+\s*\}", "", raw_answer).strip()
                except Exception:
                    pass
                    
            return raw_answer, confidence, synthesis_chunks
            
        except Exception as e:
            print(f"LLM API completion failed: {e}. Reverting to zero-cost offline matcher.")
            ans, conf = self._offline_synthesize_fallback(query, synthesis_chunks)
            return ans, conf, synthesis_chunks
