import re
from typing import Any

# GDPR Art. 17 — right to erasure support: PII patterns for redaction in logs/responses
PII_PATTERNS = [
  (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
  (re.compile(r"\b\+?\d{10,15}\b"), "[PHONE_REDACTED]"),
  (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD_REDACTED]"),
]


def redact_pii(text: str) -> str:
    result = text
    for pattern, replacement in PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def build_audit_metadata(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
