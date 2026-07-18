from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import uuid

from enterprise_rag_common.config import settings

Base = declarative_base()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserORM(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")
    locale = Column(String(10), nullable=False, default="en")
    data_region = Column(String(10), nullable=False, default="EU")
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    gdpr_consent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    owner_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    data_region = Column(String(10), nullable=False, default="EU")
    locale = Column(String(10), nullable=False, default="en")
    version = Column(Integer, default=1)
    status = Column(String(50), nullable=False, default="uploaded")
    storage_path = Column(String(1000), nullable=True)
    allowed_roles = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    data_region = Column(String(10), nullable=False, default="EU")
    ip_address = Column(String(45), nullable=True)
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeedbackORM(Base):
    __tablename__ = "feedback"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    helpful = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
