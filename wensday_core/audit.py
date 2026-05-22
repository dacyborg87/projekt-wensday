"""Minimal fail-soft audit logging hooks for Wensday OS."""

import json
import os
import re
from datetime import UTC, datetime
from typing import Any

AUDIT_FILE = os.getenv("WENSDAY_AUDIT_PATH", "wensday_audit.jsonl")

REDACTION_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(api[_-]?key|token|password|passwd|secret)\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    """Redact obvious secrets from audit-safe values."""
    if isinstance(value, str):
        redacted = value
        for pattern in REDACTION_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact(item) for key, item in value.items()}
    return value


def write_audit_event(event_type: str, details: dict[str, Any] | None = None) -> bool:
    """Write one JSONL audit event. Returns False instead of raising on failure."""
    event = {
        "timestamp": _now(),
        "event_type": event_type,
        "details": redact(details or {}),
    }
    try:
        path = os.getenv("WENSDAY_AUDIT_PATH", AUDIT_FILE)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False
