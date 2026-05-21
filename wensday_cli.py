from typing import Dict, Any, Optional, List

# --- Simple conversation memory + modes for the CLI only ---

ConversationTurn = Dict[str, str]
CONVERSATION_MEMORY: List[ConversationTurn] = []

def update_memory(role: str, content: str) -> None:
    """
    Very lightweight in‑memory conversation log for the CLI.

    This keeps the last ~20 turns so we can optionally show context or
    send it along to the backend later.
    """
    CONVERSATION_MEMORY.append({"role": role, "content": content})
    # Trim to last 20 turns to avoid unbounded growth
    if len(CONVERSATION_MEMORY) > 20:
        del CONVERSATION_MEMORY[:-20]


MODES: Dict[str, Dict[str, str]] = {
    "default": {
        "label": "Default",
        "instructions": (
            "You are Wensday, a helpful assistant. Be clear, concise, and actionable. "
            "Prefer concise answers first, then expand only if the user asks.\n\n"
            "Reasoning discipline + confidence contract:\n"
            "- Always include: Confidence = low/med/high.\n"
            "- If confidence is low: say what you need to know, ask up to 2 questions, "
            "and offer safe next steps.\n"
            "- If confidence is medium: give a short rationale (1–2 lines) and next actions.\n"
            "- If confidence is high: be direct and actionable; keep rationale to 1 line max.\n"
            "- Don’t guess facts (dates, numbers, claims). If unsure, say so and propose how to verify.\n"
            "- Keep explanations tight by default; use bullets; avoid long lectures unless asked."
        ),
    },
    "coach": {
        "label": "Coach",
        "instructions": (
            "You are Wensday, a motivational but practical coach. "
            "Give direct advice, next steps, and keep answers focused on progress."
        ),
    },
    "debug": {
        "label": "Debug",
        "instructions": (
            "You are Wensday in debug mode. Explain what you are thinking step‑by‑step "
            "in plain language, and suggest concrete next debugging actions."
        ),
    },
}


def parse_mode_command(text: str, current_mode: str) -> Optional[str]:
    """
    Handle /mode commands.

    /mode             -> just show the current mode (handled by caller)
    /mode NAME        -> switch to that mode if it exists
    """
    stripped = text.strip()
    if not stripped.startswith("/mode"):
        return None

    parts = stripped.split(maxsplit=1)
    if len(parts) == 1:
        # Caller will just display the current mode
        return current_mode

    requested = parts[1].lower().strip()
    if requested in MODES:
        return requested

    print(f"Unknown mode '{requested}'. Available modes: {', '.join(MODES.keys())}")
    return current_mode


def _print_mode_help(current_mode: str) -> None:
    print("\nAvailable modes:")
    for key, cfg in MODES.items():
        marker = "*" if key == current_mode else " "
        print(f"  {marker} {key}: {cfg['label']}")
    print("\nCommands:")
    print("  /mode              -> show current mode")
    print("  /mode <name>       -> switch mode")
    print("  /help              -> show this help\n")


def apply_mode_to_user_text(user_text: str, mode: str) -> str:
    """
    Prepend the mode's instructions + a short memory summary (if any)
    to the raw user_text. This lets us keep all the 'system prompt'
    logic here in the CLI instead of the backend.
    """
    mode_cfg = MODES.get(mode, MODES["default"])
    instructions = mode_cfg["instructions"]

    # Simple 1‑line memory summary (most recent turn only, for now)
    memory_lines: List[str] = []
    if CONVERSATION_MEMORY:
        last = CONVERSATION_MEMORY[-1]
        memory_lines.append(
            f"Last interaction – {last['role']}: {last['content'][:200]}"
        )

    memory_block = ""
    if memory_lines:
        memory_block = "\n\nCONVERSATION MEMORY (most recent first):\n" + "\n".join(
            memory_lines
        )

    return f"[MODE: {mode_cfg['label']}]\n{instructions}{memory_block}\n\nUSER: {user_text}"

def main() -> None:
    """
    Simple terminal CLI for talking to Wensday.

    - Supports /mode switching
    - Streams text tokens to the terminal
    - Streams audio via wensday_voice.stream_wensday_reply
    - Lets you interrupt mid‑sentence with Ctrl+C
    """
    # Local import so this file can be edited/tested without circular import headaches.
    from wensday_voice import stream_wensday_reply

    print("Wensday CLI (type 'exit' to quit)")
    current_mode = "default"

    while True:
        try:
            user_text = input("\nYou: ").strip()
            if not user_text:
                continue

            update_memory("user", user_text)
            low = user_text.lower().strip()

            # Basic commands
            if low in {"exit", "quit"}:
                print("Bye.")
                break

            if low in {"/help", "help", "/?"}:
                _print_mode_help(current_mode)
                continue

            new_mode = parse_mode_command(user_text, current_mode)
            if new_mode is not None:
                # /mode returns current mode; treat it as a status display.
                if low in {"/mode", "mode"}:
                    print(
                        f"Mode: {current_mode} "
                        f"({MODES.get(current_mode, MODES['default'])['label']})"
                    )
                else:
                    current_mode = new_mode
                    print(
                        f"Mode set to: {current_mode} "
                        f"({MODES.get(current_mode, MODES['default'])['label']})"
                    )
                continue

            # Inject mode instructions into the user message (since stream_wensday_reply has no system kwarg)
            prompt = apply_mode_to_user_text(user_text, current_mode)

            print("\nWensday: ", end="", flush=True)

            # Stream text + voice. We buffer streamed text and only send larger chunks to TTS
            # to reduce choppiness (fewer mp3 segments, fewer `afplay` restarts).
            assistant_text = ""
            buffer = ""

            for chunk in stream_wensday_reply(prompt, voice_mode=True):
                # `stream_wensday_reply` may yield either plain strings or dicts
                if isinstance(chunk, dict):
                    token = chunk.get("sentence", "")
                else:
                    token = str(chunk)

                # Stream text to the terminal
                print(token, end="", flush=True)

                # Accumulate full assistant reply
                assistant_text += token
                buffer += token

                # If you later want to send buffered chunks elsewhere, you can reuse this splitter
                # chunks, buffer = _split_ready_chunks(buffer)

            if assistant_text.strip():
                update_memory("assistant", assistant_text)

        except KeyboardInterrupt:
            # Ctrl+C: stop current audio and give control back to the user
            print("\n[Interrupted] Stopping Wensday mid‑sentence.")
            try:
                # Import lazily so the CLI still works even if stop_current_playback
                # doesn't exist yet in wensday_voice.
                from wensday_voice import stop_current_playback

                stop_current_playback()
            except Exception:
                # Never let an audio error kill the CLI loop.
                pass
            continue

        except Exception as e:
            print(f"\n[CLI error] {e}")
            print(
                "Tip: run `python3 -c 'from wensday_voice import stream_wensday_reply; "
                "print(next(stream_wensday_reply(\"test\", voice_mode=False)))'` "
                "to sanity-check imports."
            )


if __name__ == "__main__":
    main()