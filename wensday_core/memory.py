# wensday_core/memory.py

import json
import os
from datetime import datetime

# This is the file where Wensday will store memories.
MEMORY_FILE = "wensday_memory.json"


def _load_memory():
    """Load all memories from the JSON file. Return a list."""
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except json.JSONDecodeError:
        # If the file is broken, start fresh
        return []


def _save_memory(memories):
    """Save the full list of memories back to the file."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def add_memory(text, category="general"):
    """
    Add a new memory.
    - text: what we want to remember (string)
    - category: simple label like 'lab', 'school', 'family'
    """
    memories = _load_memory()

    new_item = {
        "text": text,
        "category": category,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    memories.append(new_item)
    _save_memory(memories)


def get_recent_memories(limit=5):
    """
    Get the most recent 'limit' memories.
    """
    memories = _load_memory()
    memories_sorted = sorted(
        memories,
        key=lambda m: m.get("timestamp", ""),
        reverse=True
    )
    return memories_sorted[:limit]


def search_memories(keyword, limit=5):
    """
    Very simple search: return memories where the keyword appears in the text.
    """
    keyword = keyword.lower()
    memories = _load_memory()
    matches = [m for m in memories if keyword in m.get("text", "").lower()]
    return matches[:limit]