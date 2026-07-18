"""Document Upload Service — MinIO storage + ingestion pipeline orchestration."""

import io
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from minio import Minio
from sqlalchemy.orm import Session

from enterprise_rag_common.config import settings
from enterprise_rag_common.database import AuditLogORM, DocumentORM, get_db, init_db
from enterprise_rag_common.enums import AuditAction, DocumentStatus, SupportedLocale
from enterprise_rag_common.models import DocumentUploadResponse, HealthResponse

SERVICE_NAME = "upload-service"
ALLOWED_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "message/rfc822",
}


def _minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    client = _minio_client()
    _ensure_bucket(client)
    app.state.minio = client
    app.state.http = httpx.AsyncClient(timeout=300.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Upload Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/upload", response_model=DocumentUploadResponse)
async def upload(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    role: str = Form("viewer"),
    department: str = Form(""),
    locale: str = Form("en"),
    tags: str = Form(""),
    db: Session = Depends(get_db),
):
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES and not file.filename.endswith((".pdf", ".txt", ".csv", ".docx", ".xlsx", ".pptx")):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    content = await file.read()
    doc_id = uuid.uuid4()
    object_name = f"{owner_id}/{doc_id}/{file.filename}"

    app.state.minio.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    doc = DocumentORM(
        id=doc_id,
        filename=file.filename,
        content_type=content_type,
        size_bytes=len(content),
        owner_id=uuid.UUID(owner_id),
        department=department or None,
        data_region=settings.data_region,
        locale=locale,
        status=DocumentStatus.UPLOADED.value,
        storage_path=object_name,
        allowed_roles=["viewer", "analyst", "compliance_officer"],
        tags=tag_list,
    )
    db.add(doc)
    db.add(
        AuditLogORM(
            user_id=uuid.UUID(owner_id),
            action=AuditAction.DOCUMENT_UPLOAD.value,
            resource_type="document",
            resource_id=str(doc_id),
            data_region=settings.data_region,
            metadata_json={"filename": file.filename, "size": len(content)},
        )
    )
    db.commit()

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status=DocumentStatus.UPLOADED,
        message="Document uploaded. Call /{document_id}/process to index.",
    )


@app.post("/{document_id}/process")
async def process_document(document_id: str, body: dict, db: Session = Depends(get_db)):
    """Orchestrate: OCR → Chunking → Embedding pipeline."""
    doc = db.query(DocumentORM).filter(DocumentORM.id == uuid.UUID(document_id)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    client: httpx.AsyncClient = app.state.http

    # 1. OCR / text extraction
    ocr_resp = await client.post(
        f"{settings.ocr_service_url}/extract",
        json={"document_id": document_id, "storage_path": doc.storage_path, "content_type": doc.content_type},
    )
    ocr_resp.raise_for_status()
    extracted = ocr_resp.json()

    doc.status = DocumentStatus.OCR_DONE.value
    db.commit()

    # 2. Chunking
    chunk_resp = await client.post(
        f"{settings.chunking_service_url}/chunk",
        json={
            "document_id": document_id,
            "text": extracted["text"],
            "locale": doc.locale,
            "filename": doc.filename,
        },
    )
    chunk_resp.raise_for_status()
    chunks = chunk_resp.json()["chunks"]

    doc.status = DocumentStatus.CHUNKING.value
    db.commit()

    # 3. Embedding + vector index
    embed_resp = await client.post(
        f"{settings.embedding_service_url}/embed",
        json={"document_id": document_id, "chunks": chunks},
    )
    embed_resp.raise_for_status()

    doc.status = DocumentStatus.INDEXED.value
    db.commit()

    return {
        "document_id": document_id,
        "status": DocumentStatus.INDEXED.value,
        "chunks_indexed": len(chunks),
        "message": "Document indexed successfully",
    }
