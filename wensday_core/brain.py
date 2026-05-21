"""Core text-mode brain for Wensday.

This module is the stable production import location for Wensday's text
assistant logic. Legacy scripts can keep their existing names while importing
the shared functions from here.
"""

from wensday_core.config import get_model_name, get_openai_client
from wensday_core.memory import add_memory, get_recent_memories
from wensday_core.personality import get_wensday_system_prompt


# Global mode for Wensday:
# "general" = normal behavior
# "lab" = focus only on cybersecurity lab work
CURRENT_MODE = "general"


def categorize_message(text: str) -> str:
    """Very simple category classifier for DJ's messages."""
    lower = text.lower()

    if any(word in lower for word in ["wazuh", "suricata", "kali", "windows", "soc", "lab", "siem", "ids"]):
        return "lab"

    if any(word in lower for word in ["class", "homework", "aleks", "college", "school", "professor", "exam", "assignment"]):
        return "school"

    if any(word in lower for word in ["brand", "tiktok", "kilovision", "kilovisionmedia", "kilo", "dacyborg", "da cyborg", "wensday", "wednesday", "media", "content"]):
        return "brand"

    if any(word in lower for word in ["family", "wife", "kids", "daughters", "charmaine", "bria", "mom", "dad", "parents"]):
        return "family"

    return "conversation"


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

    recent = get_recent_memories(limit=3)

    memories_text = ""
    if recent:
        memories_text += "Here are a few recent memories about DJ and his work:\n"
        for memory in recent:
            memories_text += f"- [{memory['timestamp']}] ({memory['category']}) {memory['text']}\n"
        memories_text += "\n"

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
    try:
        client = get_openai_client()
    except RuntimeError as exc:
        return f"Wensday is not fully configured yet: {exc}"

    model = get_model_name()

    prompt = build_prompt(user_input, voice_mode=voice_mode)

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )
    except Exception as exc:
        return f"Wensday could not reach OpenAI right now: {exc}"

    reply_text = response.output_text
    category = categorize_message(user_input)

    add_memory(f"DJ said: {user_input}", category=category)
    add_memory(f"Wensday replied: {reply_text}", category=category)

    return reply_text
