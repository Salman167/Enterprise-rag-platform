"""User microservice — profiles, GDPR erasure, audit logs."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from enterprise_rag_common.config import settings
from enterprise_rag_common.database import AuditLogORM, DocumentORM, FeedbackORM, UserORM, get_db, init_db
from enterprise_rag_common.enums import AuditAction, DataRegion, SupportedLocale, UserRole
from enterprise_rag_common.models import HealthResponse, UserResponse

SERVICE_NAME = "user-service"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="User Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@app.delete("/users/{user_id}")
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """GDPR Art. 17 — cascade delete user data."""
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(DocumentORM).filter(DocumentORM.owner_id == user_id).delete()
    db.query(FeedbackORM).filter(FeedbackORM.user_id == user_id).delete()
    db.add(
        AuditLogORM(
            user_id=user_id,
            action=AuditAction.DOCUMENT_DELETE.value,
            resource_type="user",
            resource_id=str(user_id),
            data_region=user.data_region,
            metadata_json={"gdpr_erasure": True},
        )
    )
    db.delete(user)
    db.commit()
    return {"message": "User and associated data erased per GDPR Art. 17"}


@app.get("/audit-logs")
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(AuditLogORM).order_by(AuditLogORM.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "data_region": log.data_region,
            "metadata": log.metadata_json,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


def _to_response(user: UserORM) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=UserRole(user.role),
        locale=SupportedLocale(user.locale),
        data_region=DataRegion(user.data_region),
        department=user.department,
        is_active=user.is_active,
        created_at=user.created_at,
    )
