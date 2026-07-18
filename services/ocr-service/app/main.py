"""OCR / Text Extraction Service — PDF, Word, Excel, PowerPoint, plain text."""

import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from minio import Minio
from pypdf import PdfReader

from enterprise_rag_common.config import settings
from enterprise_rag_common.models import HealthResponse

SERVICE_NAME = "ocr-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.minio = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    yield


app = FastAPI(title="OCR Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


def _extract_pdf(data: bytes) -> tuple[str, list[dict]]:
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text})
    full_text = "\n\n".join(p["text"] for p in pages)
    return full_text, pages


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_xlsx(data: bytes) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for sheet in wb.worksheets:
        lines.append(f"## Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def _extract_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


@app.post("/extract")
def extract(payload: dict):
    storage_path = payload.get("storage_path")
    content_type = payload.get("content_type", "")
    if not storage_path:
        raise HTTPException(status_code=400, detail="storage_path required")

    response = app.state.minio.get_object(settings.minio_bucket, storage_path)
    data = response.read()
    response.close()
    response.release_conn()

    pages: list[dict] = []
    if "pdf" in content_type or storage_path.endswith(".pdf"):
        text, pages = _extract_pdf(data)
    elif "wordprocessingml" in content_type or storage_path.endswith(".docx"):
        text = _extract_docx(data)
    elif "spreadsheetml" in content_type or storage_path.endswith(".xlsx"):
        text = _extract_xlsx(data)
    elif content_type.startswith("text/") or storage_path.endswith((".txt", ".csv")):
        text = _extract_text(data)
    else:
        text = _extract_text(data)

    return {
        "document_id": payload.get("document_id"),
        "text": text,
        "pages": pages,
        "char_count": len(text),
        "locale_detected": _detect_locale(text),
    }


def _detect_locale(text: str) -> str:
    """Simple Arabic script detection for MENA multi-language support."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    if arabic_chars > len(text) * 0.1:
        return "ar"
    return "en"
