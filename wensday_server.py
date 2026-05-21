import os
import base64
from typing import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from wensday_core.brain import ask_wensday

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

# ---------- CONFIG: API KEYS & CLIENTS ----------

ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

eleven_client = None


def get_eleven_client():
    global eleven_client
    if eleven_client is not None:
        return eleven_client
    if ElevenLabs is None:
        raise RuntimeError("The elevenlabs package is not installed. Run: pip install -r requirements.txt")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set. Audio output is disabled until it is configured.")
    eleven_client = ElevenLabs(api_key=api_key)
    return eleven_client

# ---------- FASTAPI APP SETUP ----------

app = FastAPI()

# Allow your browser UI to call this API (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can lock this down later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeakRequest(BaseModel):
    prompt: str


class SpeakResponse(BaseModel):
    text: str
    audio_base64: str


# ---------- HELPER: CONVERT STREAM TO BYTES ----------

def stream_to_bytes(stream: Iterator[bytes]) -> bytes:
    """Take ElevenLabs streaming audio and turn it into one bytes blob."""
    return b"".join(stream)


# ---------- MAIN ENDPOINT FOR YOUR UI ----------

@app.post("/api/speak", response_model=SpeakResponse)
def speak(req: SpeakRequest):
    """
    - Takes text from the UI
    - Gets Wensday's reply (text)
    - Sends reply to ElevenLabs
    - Returns both the text AND audio (base64) to the browser
    """
    # 1) Get Wensday's reply, already in your tone
    reply_text = ask_wensday(req.prompt, voice_mode=True)

    if not os.environ.get("ELEVENLABS_API_KEY") or not os.environ.get("ELEVENLABS_VOICE_ID"):
        return SpeakResponse(text=reply_text, audio_base64="")

    # 2) Generate audio with ElevenLabs (stream)
    audio_stream = get_eleven_client().text_to_speech.convert(
        text=reply_text,
        voice_id=os.environ.get("ELEVENLABS_VOICE_ID"),
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # 3) Turn the stream into raw bytes
    audio_bytes = stream_to_bytes(audio_stream)

    # 4) Base64 encode so it can travel over JSON
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return SpeakResponse(text=reply_text, audio_base64=audio_b64)
