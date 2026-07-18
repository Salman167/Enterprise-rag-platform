"""API Gateway — single entry point for all Enterprise RAG microservices."""

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from enterprise_rag_common.config import settings
from enterprise_rag_common.enums import AuditAction
from enterprise_rag_common.gdpr import redact_pii
from enterprise_rag_common.models import (
    FeedbackRequest,
    HealthResponse,
    LoginRequest,
    QueryRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from enterprise_rag_common.security import decode_access_token

SERVICE_NAME = "api-gateway"
bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=120.0)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="Enterprise RAG — API Gateway",
    description="EU/MENA-compliant enterprise knowledge search platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def proxy_request(
    request: Request,
    base_url: str,
    path: str,
    method: str = "GET",
    json_body: dict | None = None,
    files: dict | None = None,
    data: dict | None = None,
    headers: dict | None = None,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    client: httpx.AsyncClient = request.app.state.http
    auth_header = request.headers.get("Authorization")
    req_headers = headers or {}
    if auth_header:
        req_headers["Authorization"] = auth_header

    response = await client.request(method, url, json=json_body, files=files, data=data, headers=req_headers)
    if response.status_code >= 400:
        detail = response.text
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                detail = response.json()
            except Exception:
                detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(payload: UserCreate, request: Request):
    return await proxy_request(request, settings.auth_service_url, "/register", "POST", payload.model_dump(mode="json"))


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
    return await proxy_request(request, settings.auth_service_url, "/login", "POST", payload.model_dump())


@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_me(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, settings.user_service_url, f"/users/{user['sub']}")


@app.post("/api/v1/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    department: str | None = Form(None),
    locale: str = Form("en"),
    tags: str = Form(""),
    user: dict = Depends(get_current_user),
):
    files = {"file": (file.filename, await file.read(), file.content_type or "application/octet-stream")}
    data = {"department": department or "", "locale": locale, "tags": tags, "owner_id": user["sub"], "role": user["role"]}
    return await proxy_request(request, settings.upload_service_url, "/upload", "POST", files=files, data=data)


@app.get("/api/v1/documents")
async def list_documents(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, settings.metadata_service_url, f"/documents?owner_id={user['sub']}&role={user['role']}")


@app.post("/api/v1/documents/{document_id}/index")
async def index_document(document_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Trigger full ingestion pipeline: OCR → Chunk → Embed → Index."""
    return await proxy_request(
        request,
        settings.upload_service_url,
        f"/{document_id}/process",
        "POST",
        json_body={"owner_id": user["sub"], "role": user["role"]},
    )


@app.post("/api/v1/query")
async def query(payload: QueryRequest, request: Request, user: dict = Depends(get_current_user)):
  body = payload.model_dump(mode="json")
  body["user_id"] = user["sub"]
  body["role"] = user["role"]
  if settings.enable_pii_redaction:
      body["question"] = redact_pii(body["question"])
  return await proxy_request(request, settings.query_service_url, "/query", "POST", body)


@app.post("/api/v1/feedback")
async def feedback(payload: FeedbackRequest, request: Request, user: dict = Depends(get_current_user)):
    body = payload.model_dump(mode="json")
    body["user_id"] = user["sub"]
    return await proxy_request(request, settings.feedback_service_url, "/feedback", "POST", body)


@app.get("/api/v1/audit-logs")
async def audit_logs(request: Request, user: dict = Depends(get_current_user)):
    if user.get("role") not in ("admin", "compliance_officer"):
        raise HTTPException(status_code=403, detail="RBAC: compliance role required")
    return await proxy_request(request, settings.user_service_url, "/audit-logs")


@app.delete("/api/v1/users/me")
async def gdpr_delete_account(request: Request, user: dict = Depends(get_current_user)):
    """GDPR Art. 17 — Right to erasure."""
    return await proxy_request(request, settings.user_service_url, f"/users/{user['sub']}", "DELETE")
