"""Chunking Service — semantic chunking with locale-aware separators (EN/AR)."""

import re
import uuid

from fastapi import FastAPI, HTTPException

from enterprise_rag_common.config import settings
from enterprise_rag_common.models import HealthResponse

SERVICE_NAME = "chunking-service"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# Arabic-aware sentence boundaries
SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟。])\s+")

app = FastAPI(title="Chunking Service", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


def _split_text(text: str, locale: str) -> list[str]:
    if not text.strip():
        return []

    sentences = SENTENCE_SPLIT.split(text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= CHUNK_SIZE:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            if len(sentence) > CHUNK_SIZE:
                for i in range(0, len(sentence), CHUNK_SIZE - CHUNK_OVERLAP):
                    chunks.append(sentence[i : i + CHUNK_SIZE])
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    # Overlap: prepend tail of previous chunk for context continuity
    if CHUNK_OVERLAP > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-CHUNK_OVERLAP:]
            overlapped.append(f"{tail} {chunks[i]}".strip())
        chunks = overlapped

    return chunks


@app.post("/chunk")
def chunk(payload: dict):
    text = payload.get("text", "")
    document_id = payload.get("document_id")
    locale = payload.get("locale", "en")
    filename = payload.get("filename", "")

    if not document_id:
        raise HTTPException(status_code=400, detail="document_id required")

    raw_chunks = _split_text(text, locale)
    chunks = [
        {
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "text": c,
            "page_number": None,
            "chunk_index": idx,
            "locale": locale,
            "metadata": {"filename": filename, "data_region": settings.data_region},
        }
        for idx, c in enumerate(raw_chunks)
    ]

    return {"document_id": document_id, "chunks": chunks, "total_chunks": len(chunks)}
