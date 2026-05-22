"""Canonical long-term memory helpers for Wensday.

The store remains a local JSON file for now. New records use a structured
schema, while older ``text/category/timestamp`` memories still load.
"""

import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

MEMORY_FILE = os.getenv("WENSDAY_MEMORY_PATH", "wensday_memory.json")

DEFAULT_CATEGORY = "general"
DEFAULT_SENSITIVITY = "normal"
DEFAULT_SOURCE = "user_explicit"

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(api[_-]?key|token|password|passwd|secret)\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b"),
]

CATEGORY_KEYWORDS = {
    "soc_lab": {"wazuh", "suricata", "kali", "windows", "soc", "lab", "siem", "ids", "alert", "vm"},
    "learning": {"class", "homework", "aleks", "college", "school", "exam", "assignment", "learn", "study"},
    "projects": {"project", "wensday", "dacyborg", "kilovision", "brand", "content", "build", "app"},
    "family": {"family", "wife", "kids", "daughters", "mom", "dad", "parents"},
    "schedule": {"schedule", "shift", "work", "calendar", "appointment", "routine"},
    "goals": {"goal", "plan", "roadmap", "career", "target", "future"},
    "preferences": {"prefer", "prefers", "preference", "style", "likes", "explain", "tone"},
}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _memory_path(path: str | None = None) -> str:
    return path or os.getenv("WENSDAY_MEMORY_PATH", MEMORY_FILE)


def _load_raw_memory(path: str | None = None) -> list[dict[str, Any]]:
    memory_path = _memory_path(path)
    if not os.path.exists(memory_path):
        return []

    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [item for item in data["items"] if isinstance(item, dict)]
    return []


def _save_memory(memories: list[dict[str, Any]], path: str | None = None) -> None:
    memory_path = _memory_path(path)
    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def _title_from_content(content: str) -> str:
    clean = " ".join(content.split())
    if len(clean) <= 60:
        return clean or "Memory"
    return clean[:57].rstrip() + "..."


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) >= 3}


def _infer_category(text: str, fallback: str = DEFAULT_CATEGORY) -> str:
    text_tokens = _tokens(text)
    best_category = fallback
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = len(text_tokens & keywords)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def _normalize_memory(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize old and new memory records to the structured shape."""
    if "content" in item:
        content = str(item.get("content") or "")
        created_at = str(item.get("created_at") or item.get("timestamp") or _now())
        return {
            "id": str(item.get("id") or f"mem_{uuid.uuid4().hex}"),
            "category": str(item.get("category") or DEFAULT_CATEGORY),
            "title": str(item.get("title") or _title_from_content(content)),
            "content": content,
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
            "sensitivity": str(item.get("sensitivity") or DEFAULT_SENSITIVITY),
            "created_at": created_at,
            "updated_at": str(item.get("updated_at") or created_at),
            "source": str(item.get("source") or DEFAULT_SOURCE),
        }

    content = str(item.get("text") or "")
    created_at = str(item.get("timestamp") or _now())
    return {
        "id": str(item.get("id") or f"legacy_{uuid.uuid4().hex}"),
        "category": str(item.get("category") or DEFAULT_CATEGORY),
        "title": str(item.get("title") or _title_from_content(content)),
        "content": content,
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        "sensitivity": str(item.get("sensitivity") or DEFAULT_SENSITIVITY),
        "created_at": created_at,
        "updated_at": str(item.get("updated_at") or created_at),
        "source": str(item.get("source") or "legacy"),
    }


def _load_memory(path: str | None = None) -> list[dict[str, Any]]:
    """Load all memories from JSON and normalize legacy records."""
    return [_normalize_memory(item) for item in _load_raw_memory(path)]


def contains_secret(text: str) -> bool:
    """Return True if text appears to include a secret or credential."""
    return any(pattern.search(text or "") for pattern in SECRET_PATTERNS)


def add_memory(
    content: str,
    category: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    sensitivity: str = DEFAULT_SENSITIVITY,
    source: str = DEFAULT_SOURCE,
) -> dict[str, Any]:
    """Add a structured memory, blocking obvious secrets."""
    content = " ".join(str(content or "").split())
    if not content:
        raise ValueError("Cannot save an empty memory.")
    if contains_secret(content):
        raise ValueError("That looks like a secret or credential, so I will not save it.")

    now = _now()
    category = category or _infer_category(content)
    new_item = {
        "id": f"mem_{uuid.uuid4().hex}",
        "category": category,
        "title": title or _title_from_content(content),
        "content": content,
        "tags": tags or [],
        "sensitivity": sensitivity,
        "created_at": now,
        "updated_at": now,
        "source": source,
    }

    memories = _load_memory()
    memories.append(new_item)
    _save_memory(memories)
    return new_item


def get_recent_memories(limit: int = 5) -> list[dict[str, Any]]:
    """Get the most recent memories."""
    memories = _load_memory()
    memories_sorted = sorted(memories, key=lambda m: m.get("updated_at", ""), reverse=True)
    return memories_sorted[:limit]


def search_memories(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search memories by keyword across title, content, category, and tags."""
    query = (keyword or "").lower().strip()
    if not query:
        return get_recent_memories(limit=limit)

    memories = _load_memory()
    matches = []
    for memory in memories:
        haystack = " ".join(
            [
                str(memory.get("title", "")),
                str(memory.get("content", "")),
                str(memory.get("category", "")),
                " ".join(str(tag) for tag in memory.get("tags", [])),
            ]
        ).lower()
        if query in haystack:
            matches.append(memory)
    return matches[:limit]


def _score_memory(memory: dict[str, Any], user_input: str) -> int:
    input_tokens = _tokens(user_input)
    memory_text = " ".join(
        [
            str(memory.get("title", "")),
            str(memory.get("content", "")),
            str(memory.get("category", "")),
            " ".join(str(tag) for tag in memory.get("tags", [])),
        ]
    )
    memory_tokens = _tokens(memory_text)

    score = len(input_tokens & memory_tokens) * 3
    inferred = _infer_category(user_input, fallback="")
    if inferred and inferred == memory.get("category"):
        score += 4
    if memory.get("sensitivity") == "private":
        score -= 1
    return score


def get_relevant_memories(user_input: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return relevant memories using simple keyword and category scoring."""
    memories = _load_memory()
    scored = [(memory, _score_memory(memory, user_input)) for memory in memories]
    relevant = [item for item in scored if item[1] > 0]
    relevant.sort(key=lambda item: (item[1], item[0].get("updated_at", "")), reverse=True)
    if relevant:
        return [memory for memory, _score in relevant[:limit]]
    return get_recent_memories(limit=min(limit, 3))


def forget_memory(query: str) -> list[dict[str, Any]]:
    """Forget memories matching an id or text query. Returns removed items."""
    query = (query or "").strip().lower()
    if not query:
        return []

    memories = _load_memory()
    kept = []
    removed = []
    for memory in memories:
        haystack = " ".join(
            [
                str(memory.get("id", "")),
                str(memory.get("title", "")),
                str(memory.get("content", "")),
                str(memory.get("category", "")),
            ]
        ).lower()
        if query in haystack:
            removed.append(memory)
        else:
            kept.append(memory)

    if removed:
        _save_memory(kept)
    return removed


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    """Format memories compactly for prompt context."""
    lines = []
    for memory in memories:
        title = memory.get("title") or "Memory"
        category = memory.get("category") or DEFAULT_CATEGORY
        content = memory.get("content") or ""
        lines.append(f"- ({category}) {title}: {content}")
    return "\n".join(lines)
