# Enterprise RAG Platform

**EU/MENA-compliant microservices RAG platform** for GenAI Engineer portfolios targeting Europe and Arab Gulf markets.

> Built for roles: GenAI Engineer · AI Engineer · MLOps Engineer

## What Makes This Different

| Feature | EU Relevance | MENA/Arab Relevance |
|---------|-------------|---------------------|
| GDPR Art. 17 erasure | Right to delete user + document data | PDPL (Saudi/UAE) alignment |
| Audit logging | Banking, insurance, legal compliance | Financial sector regulations |
| Data region tagging (`EU` / `MENA`) | EU data residency requirements | Sovereign cloud deployments |
| Multi-language (EN, AR, FR, DE) | France, Germany, EU institutions | Arabic enterprise search |
| RBAC + document permissions | Healthcare, banking access control | Government & oil/gas sectors |
| Source citations | Legal defensibility | Audit trail for decisions |
| Hybrid search | Better precision for regulated docs | Arabic + English mixed corpora |
| Feedback loop | Continuous model improvement | Quality monitoring |

## Architecture

```
Users → API Gateway → Auth → Microservices → Qdrant / PostgreSQL / MinIO / Redis
                              ├── Upload → OCR → Chunking → Embedding
                              └── Query (LangGraph) → Retrieval → Citation → LLM
```

### Microservices (12)

| Service | Port | Responsibility |
|---------|------|----------------|
| api-gateway | 8000 | Single entry, routing, GDPR PII redaction |
| auth-service | 8001 | JWT, RBAC, GDPR consent |
| user-service | 8002 | Profiles, erasure, audit logs |
| upload-service | 8003 | MinIO storage, pipeline orchestration |
| ocr-service | 8004 | PDF/Word/Excel/PPT text extraction |
| chunking-service | 8005 | Locale-aware semantic chunking |
| embedding-service | 8006 | OpenAI embeddings → Qdrant |
| metadata-service | 8007 | Document catalog, RBAC |
| retrieval-service | 8008 | Hybrid semantic + keyword search |
| query-service | 8009 | LangGraph RAG orchestration |
| citation-service | 8010 | Source attribution |
| feedback-service | 8011 | Quality feedback loop |

## Quick Start

### Prerequisites

- Docker Desktop
- OpenAI API key (optional — dev fallback works without it)

### 1. Configure environment

```bash
cp .env.example .env
# Edit OPENAI_API_KEY in .env for production-quality answers
```

### 2. Start all services

```bash
docker compose up -d --build
```

### 3. Verify health

```bash
curl http://localhost:8000/health
```

### 4. Login (seeded admin)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@enterprise-rag.eu","password":"Admin@12345"}'
```

### 5. Upload & index a document

```bash
TOKEN="<access_token_from_login>"

curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./docs/sample-policy.pdf" \
  -F "department=Compliance" \
  -F "locale=en"

curl -X POST http://localhost:8000/api/v1/documents/<document_id>/index \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is our data retention policy?","locale":"en","hybrid":true}'
```

## Production Deployment (EU / MENA)

| Component | EU Recommendation | MENA Recommendation |
|-----------|-------------------|---------------------|
| LLM | Azure OpenAI (Sweden/West Europe) | Azure OpenAI UAE / local LLM |
| Vector DB | Qdrant on AKS/EKS eu-west-1 | Qdrant on Azure UAE |
| Object Storage | AWS S3 eu-west-1 / Azure Blob EU | AWS me-south-1 / OCI KSA |
| Secrets | Azure Key Vault / AWS Secrets Manager | Same, region-locked |
| K8s | EKS eu-west-1, AKS West Europe | AKS UAE North, OKE |
| CI/CD | GitHub Actions → ArgoCD | Same pattern |
| Monitoring | Prometheus + Grafana + Loki | Same, PDPL-compliant logging |

## Project Roadmap

- [x] Phase 1: Microservices scaffold + Docker Compose
- [x] Phase 2: Ingestion pipeline (Upload → OCR → Chunk → Embed)
- [x] Phase 3: RAG query with LangGraph + citations
- [x] Phase 4: GDPR/RBAC/multi-language foundations
- [ ] Phase 5: SharePoint/Confluence connectors
- [ ] Phase 6: Helm charts + ArgoCD GitOps
- [ ] Phase 7: Prometheus metrics + Grafana dashboards
- [ ] Phase 8: React admin UI with Arabic RTL

## API Documentation

Once running: http://localhost:8000/docs

## License

Apache-2.0
