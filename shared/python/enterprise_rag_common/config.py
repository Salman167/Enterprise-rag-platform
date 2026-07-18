from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Enterprise RAG Platform"
    app_env: str = "development"
    data_region: str = "EU"
    default_locale: str = "en"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "enterprise_rag"
    postgres_user: str = "rag_user"
    postgres_password: str = "rag_password"

    redis_host: str = "localhost"
    redis_port: int = 6379

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "enterprise_documents"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "enterprise-documents"
    minio_secure: bool = False

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    auth_service_url: str = "http://localhost:8001"
    user_service_url: str = "http://localhost:8002"
    upload_service_url: str = "http://localhost:8003"
    ocr_service_url: str = "http://localhost:8004"
    chunking_service_url: str = "http://localhost:8005"
    embedding_service_url: str = "http://localhost:8006"
    metadata_service_url: str = "http://localhost:8007"
    retrieval_service_url: str = "http://localhost:8008"
    query_service_url: str = "http://localhost:8009"
    citation_service_url: str = "http://localhost:8010"
    feedback_service_url: str = "http://localhost:8011"

    audit_log_retention_days: int = 365
    enable_pii_redaction: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
