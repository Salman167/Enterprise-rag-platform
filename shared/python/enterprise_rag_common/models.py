from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field

from enterprise_rag_common.enums import DataRegion, DocumentStatus, SupportedLocale, UserRole


class HealthResponse(BaseModel):
    service: str
    status: str = "healthy"
    version: str = "0.1.0"
    data_region: str = "EU"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.VIEWER
    locale: SupportedLocale = SupportedLocale.EN
    data_region: DataRegion = DataRegion.EU
    department: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    locale: SupportedLocale
    data_region: DataRegion
    department: str | None = None
    is_active: bool = True
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    status: DocumentStatus
    message: str


class DocumentMetadata(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    filename: str
    content_type: str
    size_bytes: int
    owner_id: UUID
    department: str | None = None
    data_region: DataRegion = DataRegion.EU
    locale: SupportedLocale = SupportedLocale.EN
    version: int = 1
    status: DocumentStatus = DocumentStatus.UPLOADED
    storage_path: str | None = None
    allowed_roles: list[UserRole] = Field(default_factory=lambda: [UserRole.VIEWER, UserRole.ANALYST])
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChunkPayload(BaseModel):
    chunk_id: str
    document_id: UUID
    text: str
    page_number: int | None = None
    chunk_index: int
    locale: SupportedLocale = SupportedLocale.EN
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    document_id: UUID
    chunks: list[ChunkPayload]


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    locale: SupportedLocale | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    hybrid: bool = True
    include_citations: bool = True
    department_filter: str | None = None


class Citation(BaseModel):
    document_id: UUID
    filename: str
    page_number: int | None = None
    chunk_index: int
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    locale: SupportedLocale
    query_id: UUID = Field(default_factory=uuid4)
    model: str


class FeedbackRequest(BaseModel):
    query_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    helpful: bool = True


class AuditLogEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    data_region: DataRegion = DataRegion.EU
    ip_address: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
