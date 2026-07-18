# Enterprise RAG Platform — Architecture

## Design Principles

1. **Microservice boundaries** — each service owns one capability and scales independently
2. **EU/MENA compliance by design** — not bolted on later
3. **Event-driven ingestion** — upload triggers async pipeline (OCR → chunk → embed)
4. **Hybrid retrieval** — 70% semantic + 30% keyword for regulated document accuracy

## Data Flow

### Ingestion

```
Client → API Gateway → Upload Service → MinIO
                      ↓
              OCR Service (text extraction)
                      ↓
              Chunking Service (locale-aware)
                      ↓
              Embedding Service → Qdrant
                      ↓
              Metadata Service → PostgreSQL
```

### Query

```
Client → API Gateway → Query Service (LangGraph)
                              ↓
                      Retrieval Service (Qdrant hybrid search)
                              ↓
                      Citation Service
                              ↓
                      OpenAI / Azure OpenAI
                              ↓
                      Response with citations
```

## GDPR Controls

- **Art. 17** — `DELETE /api/v1/users/me` cascades user documents and vectors
- **Art. 30** — Audit log table records all data access
- **PII redaction** — Query gateway redacts emails/phones in logs
- **Data region** — All records tagged `EU` or `MENA`
- **Consent** — Registration records GDPR consent flag

## RBAC Model

| Role | Upload | Query | Audit Logs | Delete Users |
|------|--------|-------|------------|--------------|
| admin | ✅ | ✅ | ✅ | ✅ |
| compliance_officer | ✅ | ✅ | ✅ | ❌ |
| analyst | ✅ | ✅ | ❌ | ❌ |
| viewer | ❌ | ✅ | ❌ | ❌ |

## Tech Stack

- **API**: FastAPI
- **Orchestration**: LangGraph
- **Vector DB**: Qdrant
- **Relational DB**: PostgreSQL
- **Cache**: Redis (reserved for session/rate limiting)
- **Object Storage**: MinIO (S3-compatible)
- **Containers**: Docker Compose (dev), Kubernetes (prod)
- **IaC**: Terraform (AWS EU regions)
- **CI**: GitHub Actions
