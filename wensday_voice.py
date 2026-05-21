import os
import subprocess
import tempfile
from typing import Generator, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

# ------------------------------------------------------------
# ElevenLabs configuration
# ------------------------------------------------------------

# API key is read from the environment for safety.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Text-to-speech model (you can override via env if needed)
MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Voice IDs (locked to DJ's preferred Wensday voice)
# If you ever want to change voices, update this ID or the ELEVENLABS_VOICE env var.
VOICE_DEFAULT = os.getenv("ELEVENLABS_VOICE", "IGB3QFVQV43GPC7NbgZO")
VOICE_SOC = VOICE_DEFAULT
VOICE_CREATOR = VOICE_DEFAULT

_client = None
_current_playback = None


def _get_client():
    """Create the ElevenLabs client only when TTS is actually used."""
    global _client
    if _client is not None:
        return _client
    if ElevenLabs is None:
        raise RuntimeError("The elevenlabs package is not installed. Run: pip install -r requirements.txt")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set. Voice output is disabled until it is configured.")
    _client = ElevenLabs(api_key=api_key)
    return _client


def _tts_to_temp_file(text: str, voice_id: str) -> str:
    """
    Synthesize `text` using ElevenLabs and write it to a temporary mp3 file.

    Returns the file path so the CLI can play it (with `afplay` on macOS).
    """
    # Stream audio from ElevenLabs
    client = _get_client()
    audio_stream = client.text_to_speech.convert(
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
            global _current_playback
            _current_playback = subprocess.Popen(["afplay", audio_path])
        except Exception as e:
            # Fail soft: log the error but still return text
            import sys
            print(f"[wensday_voice] TTS error: {e}", file=sys.stderr)

    # Always yield the text so the CLI can display it
    yield text


def stop_current_playback() -> None:
    """Best-effort stop for the current local audio playback process."""
    global _current_playback
    if _current_playback is None:
        return
    try:
        if _current_playback.poll() is None:
            _current_playback.terminate()
    except Exception:
        pass
    finally:
        _current_playback = None
