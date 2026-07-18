from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    ANALYST = "analyst"
    VIEWER = "viewer"


class DataRegion(str, Enum):
    EU = "EU"
    MENA = "MENA"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    OCR_PENDING = "ocr_pending"
    OCR_DONE = "ocr_done"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class SupportedLocale(str, Enum):
    EN = "en"
    AR = "ar"
    FR = "fr"
    DE = "de"


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    QUERY = "query"
    FEEDBACK = "feedback"
    ACCESS_DENIED = "access_denied"
    DATA_EXPORT = "data_export"
    CONSENT_UPDATE = "consent_update"
