"""LLM helpers — OpenAI with dev-mode fallback when no valid API key."""

import hashlib
import logging

from openai import APIConnectionError, AuthenticationError, OpenAI

from enterprise_rag_common.config import settings

logger = logging.getLogger(__name__)
VECTOR_SIZE = 1536
PLACEHOLDER_KEYS = {"", "sk-your-key-here", "sk-your-key", "changeme"}


def has_valid_openai_key() -> bool:
    key = (settings.openai_api_key or "").strip()
    if not key or key.lower() in PLACEHOLDER_KEYS:
        return False
    return key.startswith("sk-") and len(key) > 20


def dev_embed_text(text: str, size: int = VECTOR_SIZE) -> list[float]:
    """Deterministic local embedding for dev/demo without OpenAI."""
    digest = hashlib.sha256(text.encode()).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(size)]


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    if not has_valid_openai_key():
        logger.warning("No valid OPENAI_API_KEY — using dev-mode embeddings")
        return [dev_embed_text(t) for t in texts]

    try:
        response = client.embeddings.create(model=settings.embedding_model, input=texts)
        return [item.embedding for item in response.data]
    except (APIConnectionError, AuthenticationError) as exc:
        logger.warning("OpenAI embedding failed (%s) — falling back to dev mode", exc)
        return [dev_embed_text(t) for t in texts]
