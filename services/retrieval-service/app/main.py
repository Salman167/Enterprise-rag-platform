"""Retrieval Service — hybrid semantic + keyword search via Qdrant."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from enterprise_rag_common.config import settings
from enterprise_rag_common.llm import dev_embed_text, embed_texts, has_valid_openai_key
from enterprise_rag_common.models import HealthResponse

SERVICE_NAME = "retrieval-service"
VECTOR_SIZE = 1536


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    app.state.openai = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    yield


app = FastAPI(title="Retrieval Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


def _embed_query(query: str) -> list[float]:
    vectors = embed_texts(app.state.openai, [query])
    return vectors[0]


def _keyword_score(query: str, text: str) -> float:
    query_tokens = set(query.lower().split())
    text_tokens = set(text.lower().split())
    if not query_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


@app.post("/search")
def search(payload: dict):
    question = payload.get("question", "")
    top_k = payload.get("top_k", 5)
    hybrid = payload.get("hybrid", True)
    locale = payload.get("locale")
    department = payload.get("department_filter")

    if not question:
        raise HTTPException(status_code=400, detail="question required")

    vector = _embed_query(question)
    filters = []
    if locale:
        filters.append(FieldCondition(key="locale", match=MatchValue(value=locale)))
    if department:
        filters.append(FieldCondition(key="department", match=MatchValue(value=department)))

    query_filter = Filter(must=filters) if filters else None

    response = app.state.qdrant.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k * 2 if hybrid else top_k,
        query_filter=query_filter,
    )
    results = response.points

    hits = []
    for hit in results:
        payload = hit.payload or {}
        text = payload.get("text", "")
        semantic_score = hit.score
        kw_score = _keyword_score(question, text) if hybrid else 0.0
        combined = 0.7 * semantic_score + 0.3 * kw_score if hybrid else semantic_score

        hits.append({
            "document_id": payload.get("document_id"),
            "chunk_index": payload.get("chunk_index"),
            "text": text,
            "filename": payload.get("filename", ""),
            "page_number": payload.get("page_number"),
            "locale": payload.get("locale", "en"),
            "score": round(combined, 4),
        })

    hits.sort(key=lambda x: x["score"], reverse=True)
    return {"results": hits[:top_k], "total": len(hits[:top_k])}
