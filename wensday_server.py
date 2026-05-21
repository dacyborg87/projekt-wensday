import os
import base64
from typing import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from elevenlabs.client import ElevenLabs
from wensday_voice import ask_wensday

# ---------- CONFIG: API KEYS & CLIENTS ----------

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in the environment")

if not ELEVEN_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY is not set in the environment")

if not VOICE_ID:
    raise RuntimeError("ELEVENLABS_VOICE_ID is not set in the environment")

# ElevenLabs client
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

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

    # 2) Generate audio with ElevenLabs (stream)
    audio_stream = eleven_client.text_to_speech.convert(
        text=reply_text,
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # 3) Turn the stream into raw bytes
    audio_bytes = stream_to_bytes(audio_stream)

    # 4) Base64 encode so it can travel over JSON
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return SpeakResponse(text=reply_text, audio_base64=audio_b64)