# Enterprise RAG Platform — Testing Guide

## What Has Been Tested (✅)

| Area | Test | Result |
|------|------|--------|
| Infrastructure | `docker compose up -d --build` — 16 containers | ✅ Running |
| Health | `GET /health` on API Gateway | ✅ OK |
| Auth | Login (`admin@enterprise-rag.eu` / `Admin@12345`) | ✅ JWT issued |
| Upload | `POST /api/v1/documents/upload` with `sample-policy.txt` | ✅ Document stored |
| Indexing | `POST /api/v1/documents/{id}/index` | ✅ Status: indexed |
| Query (EN) | `POST /api/v1/query` with `locale: en` | ✅ 200 OK, citations returned |
| Retrieval | Hybrid search (semantic + keyword) | ✅ ~3 chunks, score ~0.72 |
| Dev fallback | OpenAI blocked on corporate network | ✅ Falls back gracefully |
| MinIO | Port remapped to 9100 (corporate conflict) | ✅ Working |

## Not Yet Tested (⏳)

| Area | Priority |
|------|----------|
| Multi-language upload + query (AR, FR, DE) | **High — start here** |
| RBAC / role-based document access | High |
| GDPR erasure (`DELETE` user/document) | High |
| Audit log endpoints | Medium |
| Feedback loop (`POST /api/v1/feedback`) | Medium |
| PII redaction in gateway logs | Medium |
| Wrong-locale query (negative test) | Medium |
| PDF/Word upload (OCR pipeline) | Medium |
| SharePoint/Confluence connectors | Phase 5 |
| K8s / Helm deployment | Phase 6 |
| Prometheus + Grafana | Phase 7 |
| React UI with Arabic RTL | Phase 8 |

---

## Multi-Language Testing (EN, AR, FR, DE)

### Sample files

| Language | File | Upload `locale` |
|----------|------|-----------------|
| English | `docs/sample-policy.txt` | `en` |
| Arabic | `docs/policy-ar.txt` | `ar` |
| French | `docs/policy-fr.txt` | `fr` |
| German | `docs/policy-de.txt` | `de` |

### Steps (repeat for each language)

1. Open http://localhost:8000/docs
2. **Authorize** — `POST /api/v1/auth/login` → paste Bearer token
3. **Upload** — `POST /api/v1/documents/upload`
   - `file`: choose the policy file for that language
   - `locale`: `en` | `ar` | `fr` | `de`
   - `department`: `Compliance`
4. **Index** — `POST /api/v1/documents/{document_id}/index`
5. **Query** — `POST /api/v1/query` with matching locale:

**English**
```json
{
  "question": "What is our data retention policy?",
  "locale": "en",
  "hybrid": true,
  "include_citations": true
}
```

**Arabic**
```json
{
  "question": "ما هي سياسة الاحتفاظ بالبيانات لدينا؟",
  "locale": "ar",
  "hybrid": true,
  "include_citations": true
}
```

**French**
```json
{
  "question": "Quelle est notre politique de conservation des données?",
  "locale": "fr",
  "hybrid": true,
  "include_citations": true
}
```

**German**
```json
{
  "question": "Wie lautet unsere Datenaufbewahrungsrichtlinie?",
  "locale": "de",
  "hybrid": true,
  "include_citations": true
}
```

### Expected results

| Check | Pass criteria |
|-------|---------------|
| Upload | 200 OK, `locale` matches form field |
| Index | `status: indexed`, chunk count > 0 |
| Query | Citations reference the correct language file |
| Arabic chunking | Sentences split on `؟` correctly |
| Wrong locale | Query `locale: en` on Arabic doc → weaker/wrong citations |

### Dev mode note

If OpenAI is unreachable, answers show `[Dev mode — LLM unavailable]` but **citations and retrieved chunks still prove multi-language retrieval works**.

---

## Recommended Next Steps

### This week
1. Run multi-language tests above (all 4 locales)
2. Test RBAC — create user with limited role, verify document access
3. Test GDPR erasure endpoint
4. Test feedback submission after a query
5. Upload a PDF and verify OCR extraction

### Next 2 weeks
6. Push project to GitHub (`enterprise-rag-platform`)
7. Add Azure OpenAI (works behind corporate firewall + EU region)
8. Write a 2-minute demo script for interviews

### Portfolio / career
9. Record a short Loom demo (login → upload → query in EN + AR)
10. Add architecture diagram to README
11. Deploy to Azure West Europe or AWS eu-west-1

---

## Quick checklist

```
[ ] EN — upload sample-policy.txt, query in English
[ ] AR — upload policy-ar.txt, query in Arabic
[ ] FR — upload policy-fr.txt, query in French
[ ] DE — upload policy-de.txt, query in German
[ ] Wrong locale negative test
[ ] GET /api/v1/documents — verify locale per document
[ ] RBAC test
[ ] GDPR erasure test
[ ] Feedback test
[ ] GitHub push
```
