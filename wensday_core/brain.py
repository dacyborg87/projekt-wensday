"""Core text-mode brain for Wensday.

This module is the stable production import location for Wensday's text
assistant logic. Legacy scripts can keep their existing names while importing
the shared functions from here.
"""

import re

from wensday_core.config import get_model_name, get_openai_client
from wensday_core.memory import (
    add_memory,
    contains_secret,
    forget_memory,
    format_memories_for_prompt,
    get_recent_memories,
    get_relevant_memories,
    search_memories,
)
from wensday_core.personality import get_wensday_system_prompt


# Global mode for Wensday:
# "general" = normal behavior
# "lab" = focus only on cybersecurity lab work
CURRENT_MODE = "general"


def categorize_message(text: str) -> str:
    """Very simple category classifier for DJ's messages."""
    lower = text.lower()
    tokens = set(re.findall(r"[a-z0-9_]+", lower))

    if tokens & {"wazuh", "suricata", "kali", "windows", "soc", "lab", "siem", "ids"}:
        return "lab"

    if tokens & {"class", "homework", "aleks", "college", "school", "professor", "exam", "assignment"}:
        return "school"

    if (tokens & {"brand", "tiktok", "kilovision", "kilovisionmedia", "kilo", "dacyborg", "wensday", "wednesday", "media", "content"}) or "da cyborg" in lower:
        return "brand"

    if tokens & {"family", "wife", "kids", "daughters", "charmaine", "bria", "mom", "dad", "parents"}:
        return "family"

    return "conversation"


def _format_memory_list(memories: list[dict]) -> str:
    if not memories:
        return "I do not have any matching long-term memories yet."
    lines = []
    for memory in memories:
        lines.append(
            f"- {memory.get('title', 'Memory')} "
            f"[{memory.get('category', 'general')}] "
            f"({memory.get('id', 'no-id')}): {memory.get('content', '')}"
        )
    return "\n".join(lines)


def handle_memory_command(user_input: str) -> str | None:
    """Handle explicit memory commands before calling the model."""
    stripped = user_input.strip()
    lower = stripped.lower()

    if lower.startswith("remember "):
        content = stripped[len("remember "):].strip()
        if not content:
            return "Tell me what to remember after the word 'remember'."
        if contains_secret(content):
            return "I will not save that because it looks like a secret, token, password, API key, or private key."
        try:
            category = categorize_message(content)
            memory = add_memory(
                content=content,
                category=None if category == "conversation" else category,
                source="user_explicit",
            )
        except ValueError as exc:
            return str(exc)
        return f"Memory saved: {memory['title']} [{memory['category']}]"

    if lower.startswith("forget "):
        query = stripped[len("forget "):].strip()
        if not query:
            return "Tell me what memory to forget after the word 'forget'."
        removed = forget_memory(query)
        if not removed:
            return "I could not find a matching memory to forget."
        return f"Forgot {len(removed)} matching memory item(s)."

    if lower in {"what do you remember", "what do you remember?", "show memories", "list memories"}:
        return _format_memory_list(get_recent_memories(limit=10))

    if lower.startswith("search memory "):
        query = stripped[len("search memory "):].strip()
        if not query:
            return "Tell me what to search for after 'search memory'."
        return _format_memory_list(search_memories(query, limit=10))

    return None


def build_prompt(user_input: str, voice_mode: bool = False) -> str:
    """Build the full prompt string sent to the model."""
    system_prompt = get_wensday_system_prompt()

    mode_text = ""
    if CURRENT_MODE == "lab":
        mode_text = (
            "You are currently in LAB MODE.\n"
            "In this mode, focus only on DJ's cybersecurity lab: Wazuh, Suricata, Windows, Kali, networks, logs, and detections.\n"
            "Give very concrete, step-by-step instructions with no big jumps.\n"
            "Avoid talking about unrelated life topics unless they are directly needed to explain a lab concept.\n"
        )

    relevant_memories = get_relevant_memories(user_input, limit=5)

    memories_text = ""
    if relevant_memories:
        memories_text = (
            "Relevant long-term memories about DJ and his work:\n"
            + format_memories_for_prompt(relevant_memories)
            + "\n\n"
        )

    voice_flag = "VOICE_MODE: true\n" if voice_mode else ""

    return (
        system_prompt
        + "\n\n"
        + voice_flag
        + mode_text
        + memories_text
        + "Now, here is DJ's new message. Answer clearly.\n"
        + f"DJ says: {user_input}\n"
    )


def ask_wensday(user_input: str, voice_mode: bool = False) -> str:
    """Send a question or message to Wensday and get a reply."""
    from wensday_core.orchestrator import WensdayOrchestrator

    return WensdayOrchestrator().handle(user_input, voice_mode=voice_mode)
