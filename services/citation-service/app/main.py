"""Citation Service — source attribution for audit/compliance (EU legal, banking)."""

from uuid import UUID

from fastapi import FastAPI

from enterprise_rag_common.config import settings
from enterprise_rag_common.models import Citation, HealthResponse

SERVICE_NAME = "citation-service"

app = FastAPI(title="Citation Service", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


def _parse_document_id(raw: object) -> UUID | None:
    if raw is None or raw == "":
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


@app.post("/build")
def build_citations(payload: dict):
    results = payload.get("results", [])
    if not results:
        return {"citations": []}

    citations = []
    for r in results:
        document_id = _parse_document_id(r.get("document_id"))
        if document_id is None:
            continue
        excerpt = (r.get("text") or "")[:300]
        citations.append(
            Citation(
                document_id=document_id,
                filename=r.get("filename") or "unknown",
                page_number=r.get("page_number"),
                chunk_index=int(r.get("chunk_index") or 0),
                excerpt=excerpt,
                score=float(r.get("score") or 0.0),
            ).model_dump(mode="json")
        )

    return {"citations": citations, "skipped": len(results) - len(citations)}
