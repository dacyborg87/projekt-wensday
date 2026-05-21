import os
import subprocess
import tempfile
from typing import Generator, Optional

from elevenlabs.client import ElevenLabs

# ------------------------------------------------------------
# ElevenLabs configuration
# ------------------------------------------------------------

# API key is read from the environment for safety.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise RuntimeError("Missing ELEVENLABS_API_KEY env variable")

# Text-to-speech model (you can override via env if needed)
MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Voice IDs (locked to DJ's preferred Wensday voice)
# If you ever want to change voices, update this ID or the ELEVENLABS_VOICE env var.
VOICE_DEFAULT = os.getenv("ELEVENLABS_VOICE", "IGB3QFVQV43GPC7NbgZO")
VOICE_SOC = VOICE_DEFAULT
VOICE_CREATOR = VOICE_DEFAULT

# Single shared ElevenLabs client
_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def _tts_to_temp_file(text: str, voice_id: str) -> str:
    """
    Synthesize `text` using ElevenLabs and write it to a temporary mp3 file.

    Returns the file path so the CLI can play it (with `afplay` on macOS).
    """
    # Stream audio from ElevenLabs
    audio_stream = _client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=MODEL,
        text=text,
        output_format="mp3_44100_128",
    )

    fd, path = tempfile.mkstemp(prefix="wensday_chunk_", suffix=".mp3")
    with os.fdopen(fd, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    return path


def stream_wensday_reply(
    text: str,
    voice_mode: bool = True,
    voice_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Yield Wensday's reply text for the CLI.

    The CLI expects this generator to yield **strings**, not dictionaries.

    Behaviour:
    - If `voice_mode` is False:
        * Do NOT call ElevenLabs.
        * Simply yield the full `text` once.
    - If `voice_mode` is True:
        * Generate an mp3 with ElevenLabs.
        * Start playback with `afplay` in the background (non-blocking).
        * Still yield the full `text` once so the CLI can print it.
    """
    if voice_id is None:
        voice_id = VOICE_DEFAULT

    # Kick off audio playback if requested
    if voice_mode and text.strip():
        try:
            audio_path = _tts_to_temp_file(text, voice_id)
            # Play audio in the background so text printing isn't blocked
            subprocess.Popen(["afplay", audio_path])
        except Exception as e:
            # Fail soft: log the error but still return text
            import sys
            print(f"[wensday_voice] TTS error: {e}", file=sys.stderr)

    # Always yield the text so the CLI can display it
    yield text