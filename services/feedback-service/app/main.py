"""Feedback Service — RLHF-style quality loop for continuous improvement."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from enterprise_rag_common.config import settings
from enterprise_rag_common.database import AuditLogORM, FeedbackORM, get_db, init_db
from enterprise_rag_common.enums import AuditAction
from enterprise_rag_common.models import FeedbackRequest, HealthResponse

SERVICE_NAME = "feedback-service"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Feedback Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/feedback")
def submit_feedback(payload: dict, db: Session = Depends(get_db)):
    feedback = FeedbackORM(
        query_id=UUID(payload["query_id"]),
        user_id=UUID(payload["user_id"]) if payload.get("user_id") else None,
        rating=payload["rating"],
        comment=payload.get("comment"),
        helpful=payload.get("helpful", True),
    )
    db.add(feedback)
    db.add(
        AuditLogORM(
            user_id=feedback.user_id,
            action=AuditAction.FEEDBACK.value,
            resource_type="query",
            resource_id=str(feedback.query_id),
            data_region=settings.data_region,
            metadata_json={"rating": feedback.rating, "helpful": feedback.helpful},
        )
    )
    db.commit()
    return {"message": "Feedback recorded", "feedback_id": str(feedback.id)}


@app.get("/feedback/stats")
def feedback_stats(db: Session = Depends(get_db)):
    total = db.query(FeedbackORM).count()
    helpful = db.query(FeedbackORM).filter(FeedbackORM.helpful == True).count()  # noqa: E712
    return {
        "total_feedback": total,
        "helpful_rate": round(helpful / total, 2) if total else 0,
        "data_region": settings.data_region,
    }
