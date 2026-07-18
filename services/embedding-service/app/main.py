"""Embedding Service — OpenAI embeddings stored in Qdrant vector DB."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from enterprise_rag_common.config import settings
from enterprise_rag_common.llm import embed_texts, has_valid_openai_key
from enterprise_rag_common.models import HealthResponse

SERVICE_NAME = "embedding-service"
VECTOR_SIZE = 1536  # text-embedding-3-small


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    app.state.qdrant = client
    app.state.openai = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    yield


app = FastAPI(title="Embedding Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    return embed_texts(app.state.openai, texts)


@app.post("/embed")
def embed(payload: dict):
    document_id = payload.get("document_id")
    chunks = payload.get("chunks", [])
    if not document_id or not chunks:
        raise HTTPException(status_code=400, detail="document_id and chunks required")

    texts = [c["text"] for c in chunks]
    vectors = _embed_texts(texts)

    points = [
        PointStruct(
            id=c["chunk_id"],
            vector=vectors[i],
            payload={
                "document_id": document_id,
                "chunk_index": c["chunk_index"],
                "text": c["text"],
                "locale": c.get("locale", "en"),
                "filename": c.get("metadata", {}).get("filename", ""),
                "data_region": settings.data_region,
                "page_number": c.get("page_number"),
            },
        )
        for i, c in enumerate(chunks)
    ]

    app.state.qdrant.upsert(collection_name=settings.qdrant_collection, points=points)

    return {
        "document_id": document_id,
        "vectors_stored": len(points),
        "collection": settings.qdrant_collection,
    }


@app.delete("/documents/{document_id}")
def delete_document_vectors(document_id: str):
    """GDPR — remove vectors for a document."""
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    app.state.qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
    return {"message": f"Vectors deleted for document {document_id}"}
