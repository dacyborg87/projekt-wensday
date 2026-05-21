import os
import sys
import subprocess
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Tuple, Optional

from elevenlabs.client import ElevenLabs
import json
from datetime import datetime
from wensday_voice import ask_wensday

# -----------------------------
# 1. Setup ElevenLabs client
# -----------------------------
# Make sure you have ELEVENLABS_API_KEY set in your environment.
# Example (Mac):
#   export ELEVENLABS_API_KEY="sk-..."
# You only do that once per terminal session.

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY is not set in your environment.")

# ElevenLabs Voice ID for Wensday's voice
# You can override this from your terminal:
#   export ELEVENLABS_VOICE_ID="l6JdXREaWV2XUOQFjMPH"
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "l6JdXREaWV2XUOQFjMPH")


# Create ElevenLabs client instance
voice_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


# -----------------------------
# ElevenLabs voice tuning helpers
# -----------------------------

def _float_env(name: str) -> float | None:
    val = os.environ.get(name)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _build_voice_settings() -> dict:
    """Optional ElevenLabs voice settings controlled via env vars."""
    settings: dict[str, float] = {}

    stability = _float_env("ELEVENLABS_STABILITY")
    similarity = _float_env("ELEVENLABS_SIMILARITY_BOOST")
    style = _float_env("ELEVENLABS_STYLE")

    if stability is not None:
        settings["stability"] = stability
    if similarity is not None:
        settings["similarity_boost"] = similarity
    if style is not None:
        settings["style"] = style

    return settings


# -----------------------------
# Wensday "smarts" helpers (mode + lightweight memory + chat history)
# -----------------------------

MEMORY_PATH = os.environ.get("WENSDAY_MEMORY_PATH", "wensday_memory.json")
MAX_MEMORY_ITEMS = int(os.environ.get("WENSDAY_MAX_MEMORY_ITEMS", "8"))
MAX_HISTORY_TURNS = int(os.environ.get("WENSDAY_MAX_HISTORY_TURNS", "6"))


def _load_memory(path: str = MEMORY_PATH) -> list[dict]:
    """Loads structured memory items from JSON if present."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [x for x in data["items"] if isinstance(x, dict)]
        return []
    except FileNotFoundError:
        return []
    except Exception:
        # If memory is malformed, don't break voice mode
        return []


def _score_memory_item(item: dict, prompt: str) -> int:
    """Very lightweight keyword scoring to pick relevant memory without extra dependencies."""
    text = " ".join(
        str(item.get(k, ""))
        for k in ("title", "summary", "content", "text", "tags")
        if item.get(k) is not None
    ).lower()
    if not text:
        return 0

    q = prompt.lower()
    score = 0
    # Exact substring hits
    for token in set([t for t in q.replace("/", " ").replace("-", " ").split() if len(t) >= 4]):
        if token in text:
            score += 2
    # Boost if item is explicitly pinned/important
    if item.get("pinned") is True:
        score += 3
    return score


def _select_memory(prompt: str, limit: int = MAX_MEMORY_ITEMS) -> list[dict]:
    mem = _load_memory()
    if not mem:
        return []
    ranked = sorted(mem, key=lambda it: _score_memory_item(it, prompt), reverse=True)
    # Keep only items with a non-zero score; fall back to most recent if nothing matches
    picked = [it for it in ranked if _score_memory_item(it, prompt) > 0][:limit]
    if picked:
        return picked
    # If memory items have timestamps, try most recent; otherwise just take first N
    def _ts(it: dict) -> str:
        return str(it.get("ts") or it.get("timestamp") or it.get("date") or "")

    by_recent = sorted(mem, key=_ts, reverse=True)
    return by_recent[: min(limit, len(by_recent))]


def _format_memory(items: list[dict]) -> str:
    lines: list[str] = []
    for i, it in enumerate(items, start=1):
        title = str(it.get("title") or it.get("key") or f"Memory {i}").strip()
        body = str(it.get("summary") or it.get("content") or it.get("text") or "").strip()
        tags = it.get("tags")
        if isinstance(tags, list):
            tag_str = ", ".join(str(t) for t in tags[:6])
        else:
            tag_str = ""
        if body:
            lines.append(f"- {title}: {body}{(' | tags: ' + tag_str) if tag_str else ''}")
        else:
            lines.append(f"- {title}{(' | tags: ' + tag_str) if tag_str else ''}")
    return "\n".join(lines)


def _system_instructions(mode: str) -> str:
    """Mode-specific behavior. Keep this short so it doesn't bloat every request."""
    mode = (mode or "default").lower()
    base = (
        "You are Wensday, DJ's AI assistant. Be concise, practical, and correct. "
        "Ask one clarifying question only if truly necessary; otherwise make the best reasonable assumption and proceed. "
        "When giving steps, number them. When writing prompts/scripts, make them copy/paste ready."
    )

    if mode == "soc":
        return (
            base
            + "\nSOC mode: prioritize cybersecurity/defense guidance. Use safe, ethical framing. "
            + "Prefer checklists, triage steps, and commands that are defensive (monitoring, hardening, analysis)."
        )
    if mode == "creator":
        return (
            base
            + "\nCreator mode: prioritize content ideas, hooks, scripts, shot lists, captions, and clear formatting for IG/TikTok. "
            + "Keep tone motivating and brand-aligned."
        )
    return base


def _build_augmented_prompt(user_text: str, mode: str, history: List[Tuple[str, str]]) -> str:
    """Wraps the user's prompt with mode rules, selected memory, and brief chat history."""
    mem_items = _select_memory(user_text)
    mem_block = _format_memory(mem_items)

    # Include a small rolling history so the model stays coherent across turns.
    recent = history[-MAX_HISTORY_TURNS:]
    history_lines: list[str] = []
    for u, a in recent:
        history_lines.append(f"User: {u}")
        history_lines.append(f"Wensday: {a}")
    history_block = "\n".join(history_lines).strip()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts: list[str] = []
    parts.append(f"[WENSDAY SYSTEM]\nTime: {now}\nMode: {mode}\n{_system_instructions(mode)}")
    if mem_block:
        parts.append(f"\n[RELEVANT MEMORY]\n{mem_block}")
    if history_block:
        parts.append(f"\n[RECENT CONTEXT]\n{history_block}")
    parts.append(f"\n[USER REQUEST]\n{user_text}\n\n[RESPONSE]\n")
    return "\n".join(parts)

# -----------------------------
# 2. Function to talk with Wensday
# -----------------------------

def speak_with_wensday(prompt: str, mode: str, history: List[Tuple[str, str]]) -> str:
    """
    - Sends your text to Wensday (via ask_wensday with voice_mode=True).
    - Uses ElevenLabs to turn the reply into speech.
    - Streams the audio to a temp mp3 file and plays it.
    """
    print(f"You: {prompt}")
    print("Wensday is thinking...\n")

    # Ask Wensday (this uses your existing logic in wensday_voice.py)
    # We augment the prompt with: mode rules + selected memory + short rolling history
    augmented = _build_augmented_prompt(prompt, mode=mode, history=history)
    reply = ask_wensday(augmented, voice_mode=True)
    print(f"Wensday: {reply}\n")

    return reply

    # Use ElevenLabs to generate audio as a stream of chunks
    try:
        # Optional voice tuning via env vars
        voice_settings = _build_voice_settings()
        extra_kwargs = {}
        if voice_settings:
            extra_kwargs["voice_settings"] = voice_settings

        audio_stream = voice_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_multilingual_v2",
            optimize_streaming_latency=1,
            output_format="mp3_44100_128",
            text=reply,
            **extra_kwargs,
        )

        # Write the streamed bytes to a temporary mp3 file
        with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            for chunk in audio_stream:
                if chunk:
                    tmp.write(chunk)
            audio_path = tmp.name

        # Best-effort cleanup of the temp file after playback

        # Play audio depending on OS
        if sys.platform == "darwin":
            subprocess.call(["afplay", audio_path])
            try:
                os.remove(audio_path)
            except OSError:
                pass
        elif sys.platform.startswith("linux"):
            subprocess.call(["aplay", audio_path])
            try:
                os.remove(audio_path)
            except OSError:
                pass
        elif sys.platform.startswith("win"):
            subprocess.call(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync();",
                ]
            )
            try:
                os.remove(audio_path)
            except OSError:
                pass
        else:
            print("[WARN] Unsupported OS for auto-playback. Audio saved at:", audio_path)

    except Exception as e:
        print("[ERROR] Problem speaking with ElevenLabs:", e)
        print("Wensday (text-only):", reply)
        return reply

    return reply


# -----------------------------
# 3. Simple command-line loop
# -----------------------------

if __name__ == "__main__":
    print("Wensday Voice (ElevenLabs) — type 'quit' to stop.")
    print("Commands: /soc, /creator, /default, /help, /clear\n")

    mode = os.environ.get("WENSDAY_MODE", "default").lower()
    history: List[Tuple[str, str]] = []

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nWensday: Goodbye DJ.")
            break

        # Commands
        if user_text.lower() in ("/help", "help"):
            print("\nCommands:\n  /soc      - SOC/defender mode\n  /creator  - creator/content mode\n  /default  - balanced mode\n  /clear    - clear short-term chat history\n  quit      - exit\n")
            continue

        if user_text.lower() in ("/clear", "clear"):
            history = []
            print("[OK] Cleared short-term history.\n")
            continue

        if user_text.lower() in ("/soc", "/creator", "/default"):
            mode = user_text.lower().lstrip("/")
            print(f"Mode set to: {mode}\n")
            continue

        if not user_text:
            continue
        if user_text.lower() in ("quit", "exit", "q"):
            print("Wensday: Goodbye DJ.")
            break

        reply = speak_with_wensday(user_text, mode=mode, history=history)
        history.append((user_text, reply))