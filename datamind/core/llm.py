"""
LLM service for generating intelligent responses.
Supports OpenAI with Groq fallback.
"""

from typing import Optional, List

import requests

from datamind.config import settings
from datamind.utils import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for LLM-based response generation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.openai_api_key = api_key or settings.OPENAI_API_KEY
        self.openai_model = model or settings.LLM_MODEL
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_model = settings.GROQ_LLM_MODEL
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.timeout = settings.REQUEST_TIMEOUT
        self.available = bool(self.openai_api_key or self.groq_api_key)

        if self.available:
            logger.info(
                f"LLMService initialized with OpenAI model: {self.openai_model} "
                f"and Groq model: {self.groq_model}"
            )
        else:
            logger.warning("LLMService disabled: no LLM API keys configured")

    def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        if not self.available:
            logger.warning("LLM service not available, returning None")
            return None

        system_prompt = system_prompt or self._default_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"},
        ]

        try:
            return self._call_api(messages)
        except Exception as exc:
            logger.error(f"LLM generation failed: {exc}")
            return self._fallback_response(query, context)

    def _call_api(self, messages: List[dict]) -> str:
        providers = []
        if self.openai_api_key:
            providers.append(
                ("openai", self.openai_api_url, self.openai_api_key, self.openai_model)
            )
        if self.groq_api_key:
            providers.append(("groq", self.groq_api_url, self.groq_api_key, self.groq_model))

        last_error: Optional[Exception] = None

        for provider_name, api_url, api_key, model in providers:
            try:
                response = requests.post(
                    api_url,
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": settings.MAX_TOKENS,
                        "temperature": 0.7,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )

                if response.status_code >= 400:
                    logger.warning(
                        f"{provider_name.title()} LLM request failed with {response.status_code}: {response.text[:300]}"
                    )
                    last_error = RuntimeError(response.text)
                    continue

                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    choice = choices[0]
                    message = choice.get("message", {})
                    content = message.get("content") or choice.get("text")
                    if content:
                        return content

                last_error = ValueError(f"Unexpected {provider_name} response: {data}")
            except Exception as exc:
                logger.warning(f"{provider_name.title()} LLM request error: {exc}")
                last_error = exc

        raise RuntimeError(f"All LLM providers failed: {last_error}")

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "You are DataMind, an intelligent document analysis assistant. "
            "Provide concise, accurate answers based only on the supplied context. "
            "If the answer is not in the context, say so clearly."
        )

    @staticmethod
    def _fallback_response(query: str, context: str) -> str:
        excerpt = context.strip()[:1200]
        if excerpt:
            return (
                "I couldn't reach an LLM provider right now, but here are the relevant excerpts:\n\n"
                f"{excerpt}\n\nQuestion: {query}"
            )
        return f"I couldn't reach an LLM provider right now. Question: {query}"

    def verify_connection(self) -> bool:
        if not self.available:
            return False

        try:
            return bool(self._call_api([{"role": "user", "content": "test"}]))
        except Exception as exc:
            logger.error(f"LLM connection verification failed: {exc}")
            return False


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def initialize_llm_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    global _llm_service
    _llm_service = LLMService(api_key=api_key, model=model)
    return _llm_service
