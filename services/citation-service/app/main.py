"""Citation Service — source attribution for audit/compliance (EU legal, banking)."""

from uuid import UUID

from fastapi import FastAPI, HTTPException

from enterprise_rag_common.config import settings
from enterprise_rag_common.models import Citation, HealthResponse

SERVICE_NAME = "citation-service"

app = FastAPI(title="Citation Service", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/build")
def build_citations(payload: dict):
    results = payload.get("results", [])
    if not results:
        return {"citations": []}

    citations = []
    for r in results:
        excerpt = r.get("text", "")[:300]
        citations.append(
            Citation(
                document_id=UUID(r["document_id"]) if r.get("document_id") else UUID(int=0),
                filename=r.get("filename", "unknown"),
                page_number=r.get("page_number"),
                chunk_index=r.get("chunk_index", 0),
                excerpt=excerpt,
                score=r.get("score", 0.0),
            ).model_dump(mode="json")
        )

    return {"citations": citations}
