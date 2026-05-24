"""Read-only SOC dashboard routes for Wensday OS."""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse

from wensday_core.audit import AUDIT_FILE
from wensday_core.config import get_model_name
from wensday_core.memory import _load_memory
from wensday_core.orchestrator import get_latest_explainable_response
from wensday_core.plugins import build_default_registry

router = APIRouter()


def _audit_path() -> Path:
    """Read the configured Wensday audit log path from environment/default audit settings."""
    return Path(os.getenv("WENSDAY_AUDIT_PATH", AUDIT_FILE))


def _load_audit_events() -> list[dict[str, Any]]:
    """Read audit JSONL entries from the local Wensday audit log."""
    path = _audit_path()
    if not path.exists():
        return []

    events = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    events.append(item)
    except OSError:
        return []
    return events


def _severity_for_event(event_type: str) -> str:
    """Map a Wensday audit event type to the dashboard severity vocabulary."""
    if "denied" in event_type or "blocked" in event_type:
        return "deny"
    if "failed" in event_type or "error" in event_type:
        return "warn"
    if event_type in {"request_completed", "plugin_used", "memory_command"}:
        return "ok"
    return "info"


def _audit_row(event: dict[str, Any]) -> dict[str, str]:
    """Convert a raw Wensday audit event into the dashboard audit row shape."""
    details = event.get("details") if isinstance(event.get("details"), dict) else {}
    event_type = str(event.get("event_type", "event"))
    target = (
        details.get("request_type")
        or details.get("plugin")
        or details.get("reason")
        or "wensday"
    )
    return {
        "ts": str(event.get("timestamp", "")),
        "actor": str(details.get("actor", "system")),
        "action": event_type,
        "target": str(target),
        "severity": _severity_for_event(event_type),
    }


def _plugin_rows() -> list[dict[str, str]]:
    """Read the current plugin registry and add planned read-only SOC placeholders."""
    registry = build_default_registry()
    plugins = list(getattr(registry, "_plugins", []))
    rows = [
        {
            "name": getattr(plugin, "name", "unnamed"),
            "description": getattr(plugin, "description", "Read-only defensive plugin"),
            "status": "active",
            "permission_model": "read-only",
        }
        for plugin in plugins
    ]
    rows.extend(
        [
            {
                "name": "Wensday Orchestrator",
                "description": "Request classification, policy checks, memory retrieval, and response routing.",
                "status": "active",
                "permission_model": "controlled/read-only by default",
            },
            {
                "name": "Memory Store",
                "description": "Structured explicit long-term memory backed by local JSON.",
                "status": "active",
                "permission_model": "explicit write, read-only dashboard",
            },
            {
                "name": "Audit Logger",
                "description": "Fail-soft JSONL audit metadata with basic redaction.",
                "status": "active",
                "permission_model": "append-only local file",
            },
            {
                "name": "Wazuh",
                "description": "Future read-only alert summary module.",
                "status": "idle",
                "permission_model": "planned read-only",
            },
            {
                "name": "Suricata",
                "description": "Future read-only IDS event module.",
                "status": "idle",
                "permission_model": "planned read-only",
            },
        ]
    )
    return rows


def _memory_rows() -> list[dict[str, str]]:
    """Read structured Wensday memory entries through the canonical memory loader."""
    rows = []
    for memory in _load_memory():
        rows.append(
            {
                "scope": "persist",
                "key": str(memory.get("title") or memory.get("id") or "memory"),
                "value": str(memory.get("content") or ""),
            }
        )
    return rows


def _last_ai_response() -> dict[str, Any]:
    """Read the latest safe explainable response snapshot from the orchestrator."""
    latest = get_latest_explainable_response()
    if latest:
        return latest
    return {
        "query": None,
        "summary": None,
        "evidence": [],
        "reasoning": [],
        "reasoning_steps": [
            {"step": 1, "label": "No operational AI response recorded yet", "status": "skipped"},
        ],
        "output": None,
        "confidence": 0,
        "recommended_next_checks": [],
        "memory_used": [],
        "plugins_queried": [],
        "policy_result": None,
        "unverified_items": [],
        "model": get_model_name(),
        "tokens": None,
        "mitre_tags": [],
    }


@router.get("/dashboard")
async def dashboard():
    """Serve the static dashboard HTML from the local static folder."""
    return FileResponse(os.path.join("static", "dashboard.html"))


@router.get("/api/dashboard/metrics")
async def dashboard_metrics():
    """Read dashboard metrics from memory, audit log, and plugin registry modules."""
    audit_events = _load_audit_events()
    plugin_rows = _plugin_rows()
    return {
        "plugins_active": sum(1 for plugin in plugin_rows if plugin["status"] == "active"),
        "plugins_total": len(plugin_rows),
        "memory_entries": len(_load_memory()),
        "audit_event_count": len(audit_events),
        "policy_denials": sum(1 for event in audit_events if event.get("event_type") == "policy_denied"),
    }


@router.get("/api/dashboard/audit")
async def dashboard_audit():
    """Read and return the last 50 Wensday audit log entries."""
    rows = [_audit_row(event) for event in _load_audit_events()]
    return rows[-50:][::-1]


@router.get("/api/dashboard/memory")
async def dashboard_memory():
    """Read all Wensday memory entries in dashboard scope/key/value form."""
    return _memory_rows()


@router.get("/api/dashboard/plugins")
async def dashboard_plugins():
    """Read current plugin registry information and planned read-only module placeholders."""
    return _plugin_rows()


@router.get("/api/dashboard/ai/last")
async def dashboard_last_ai():
    """Read the last AI response snapshot, returning an empty placeholder when unavailable."""
    return _last_ai_response()
