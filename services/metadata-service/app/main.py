"""Metadata Service — document catalog, versioning, RBAC permissions."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from enterprise_rag_common.config import settings
from enterprise_rag_common.database import DocumentORM, get_db, init_db
from enterprise_rag_common.enums import UserRole
from enterprise_rag_common.models import HealthResponse
from enterprise_rag_common.security import can_access_document

SERVICE_NAME = "metadata-service"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Metadata Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.get("/documents")
def list_documents(owner_id: str, role: str = "viewer", db: Session = Depends(get_db)):
    user_role = UserRole(role)
    query = db.query(DocumentORM)

    if user_role != UserRole.ADMIN:
        query = query.filter(DocumentORM.owner_id == UUID(owner_id))

    docs = query.order_by(DocumentORM.created_at.desc()).all()

    if user_role != UserRole.ADMIN:
        docs = [
            d for d in docs
            if user_role.value in (d.allowed_roles or []) or d.owner_id == UUID(owner_id)
        ]
    return [_serialize(d) for d in docs]


@app.get("/documents/{document_id}")
def get_document(document_id: UUID, role: str = "viewer", db: Session = Depends(get_db)):
    doc = db.query(DocumentORM).filter(DocumentORM.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    allowed = [UserRole(r) for r in (doc.allowed_roles or [])]
    if not can_access_document(UserRole(role), allowed) and role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="RBAC: access denied")

    return _serialize(doc)


def _serialize(doc: DocumentORM) -> dict:
    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "owner_id": str(doc.owner_id),
        "department": doc.department,
        "data_region": doc.data_region,
        "locale": doc.locale,
        "version": doc.version,
        "status": doc.status,
        "tags": doc.tags or [],
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
