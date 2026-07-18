"""Authentication microservice — JWT, RBAC, GDPR consent."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from enterprise_rag_common.config import settings
from enterprise_rag_common.database import AuditLogORM, UserORM, get_db, init_db
from enterprise_rag_common.enums import AuditAction, UserRole
from enterprise_rag_common.models import HealthResponse, LoginRequest, TokenResponse, UserCreate, UserResponse
from enterprise_rag_common.security import create_access_token, hash_password, verify_password

SERVICE_NAME = "auth-service"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    _seed_admin()
    yield


def _seed_admin() -> None:
    from enterprise_rag_common.database import SessionLocal

    db = SessionLocal()
    try:
        if not db.query(UserORM).filter(UserORM.email == "admin@enterprise-rag.eu").first():
            admin = UserORM(
                email="admin@enterprise-rag.eu",
                hashed_password=hash_password("Admin@12345"),
                full_name="Platform Admin",
                role=UserRole.ADMIN.value,
                locale="en",
                data_region=settings.data_region,
                gdpr_consent=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(title="Auth Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/register", response_model=UserResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserORM).filter(UserORM.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = UserORM(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.value,
        locale=payload.locale.value,
        data_region=payload.data_region.value,
        department=payload.department,
        gdpr_consent=True,
    )
    db.add(user)
    db.add(
        AuditLogORM(
            user_id=user.id,
            action=AuditAction.CONSENT_UPDATE.value,
            resource_type="user",
            resource_id=str(user.id),
            data_region=payload.data_region.value,
            metadata_json={"gdpr_consent": True},
        )
    )
    db.commit()
    db.refresh(user)
    return _to_response(user)


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserORM).filter(UserORM.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token(str(user.id), UserRole(user.role), {"email": user.email})
    db.add(
        AuditLogORM(
            user_id=user.id,
            action=AuditAction.LOGIN.value,
            resource_type="user",
            resource_id=str(user.id),
            data_region=user.data_region,
        )
    )
    db.commit()
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)


def _to_response(user: UserORM) -> UserResponse:
    from enterprise_rag_common.enums import DataRegion, SupportedLocale

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
