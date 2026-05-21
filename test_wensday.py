# test_wensday.py
"""
Core text-mode brain for Wensday.

- Handles DJ's messages (text).
- Supports LAB mode vs GENERAL mode.
- Stores and reads memories.
- Can also be used by the voice interface (voice_mode=True).
"""

import wensday_core.brain as brain
from wensday_core.brain import ask_wensday, categorize_message, build_prompt
from wensday_core.memory import get_recent_memories

CURRENT_MODE = "general"


if __name__ == "__main__":
    print("Talk to Wensday. Type 'quit' to stop.\n")

    while True:
        user_text = input("You: ")
        cleaned = user_text.lower().strip()

        # Special command: change Wensday's mode (e.g., "mode lab" or "mode general")
        if cleaned.startswith("mode "):
            mode_name = cleaned.split(" ", 1)[1]
            if mode_name in ("lab", "general"):
                CURRENT_MODE = mode_name
                brain.CURRENT_MODE = mode_name
                print(f"\nWensday: Mode set to {CURRENT_MODE.upper()}.\n")
            else:
                print("\nWensday: I only understand 'mode lab' or 'mode general' right now.\n")
            continue

        # Special command: show recent memories without calling the model
        if cleaned == "history":
            recent = get_recent_memories(limit=5)
            if not recent:
                print("\nWensday: I don't have any memories stored yet.\n")
            else:
                print("\nWensday: Here are your last few memories:\n")
                for m in recent:
                    print(f"- [{m['timestamp']}] ({m['category']}) {m['text']}")
                print()
            continue

        if cleaned in ("quit", "exit", "q"):
            print("Wensday: Goodbye for now, DJ.")
            break

        answer = ask_wensday(user_text)
        print("\nWensday:", answer, "\n")

# wensday_voice.py
"""
Voice interface for Wensday with wake words and push-to-talk.

Flow:
1. You press Enter.
2. Wensday records audio until you hit Ctrl + C.
3. She transcribes what you said.
4. She looks for a wake word (e.g., "Hey Wensday").
5. If the wake word is present, she processes the rest as your command.
6. She sends the command to ask_wensday() and speaks the reply.
"""

import time
import wave
import subprocess
from pathlib import Path

import numpy as np
import sounddevice as sd

from wensday_core.config import get_openai_client
from wensday_core.brain import ask_wensday

AUDIO_FILENAME = "wensday_input.wav"
SAMPLE_RATE = 16000

# Wake words DJ can use
WAKE_WORDS = [
    "alright wensday",
    "hey wensday",
    "wensday",
    "yo wensday",
    "okay wensday",
]


def record_audio(filename: str, samplerate: int = SAMPLE_RATE) -> bool:
    """
    Record audio from the default microphone until the user presses Ctrl + C.
    Save it as a mono WAV file. Return True if audio was captured.
    """
    print("[Wensday] Listening... press Ctrl + C when you're done speaking.")
    frames = []

    def callback(indata, frames_count, time_info, status):
        if status:
            print(f"[Wensday] Audio status: {status}", flush=True)
        frames.append(indata.copy())

    try:
        with sd.InputStream(samplerate=samplerate, channels=1, callback=callback):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("[Wensday] Stopped recording.")

    if not frames:
        print("[Wensday] No audio captured.")
        return False

    audio_data = np.concatenate(frames, axis=0)

    # Convert float32 [-1.0, 1.0] to 16-bit PCM
    audio_int16 = (audio_data * 32767).astype("int16")

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(samplerate)
        wf.writeframes(audio_int16.tobytes())

    print(f"[Wensday] Audio saved to {filename}.")
    return True


def transcribe_audio(filename: str) -> str | None:
    """
    Use OpenAI Whisper-style transcription to convert audio to text.
    Returns the transcribed text, or None if something failed.
    """
    client = get_openai_client()
    audio_path = Path(filename)

    if not audio_path.exists():
        print("[Wensday] No audio file found to transcribe.")
        return None

    try:
        with audio_path.open("rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
            )
        text = result.text.strip()
        if not text:
            print("[Wensday] Transcription came back empty.")
            return None

        print(f"[Wensday] You said: {text}")
        return text

    except Exception as e:
        print(f"[Wensday] Transcription error: {e}")
        return None


def speak(text: str):
    """
    Speak the given text out loud using macOS 'say' command.
    """
    if not text or not text.strip():
        return

    try:
        subprocess.run(["say", text], check=False)
    except FileNotFoundError:
        print("[Wensday] Could not find 'say' to play audio.")
    except Exception as e:
        print(f"[Wensday] Speech error: {e}")


def main_loop():
    print("=== Wensday Voice (Push-to-Talk) ===")
    print("Wake words: 'Alright Wensday', 'Hey Wensday', 'Wensday', 'Yo Wensday', 'Okay Wensday'.")
    print("1) Press Enter to start recording.")
    print("2) Speak your command.")
    print("3) Press Ctrl + C when done.")
    print("Type 'exit' and press Enter to quit.\n")

    while True:
        cmd = input("Press Enter to record, or type 'exit': ").strip().lower()
        if cmd == "exit":
            print("[Wensday] Exiting voice loop. Bye DJ.")
            break

        # Step 1: Record audio
        if not record_audio(AUDIO_FILENAME):
            continue

        # Step 2: Transcribe audio
        spoken_text = transcribe_audio(AUDIO_FILENAME)
        if not spoken_text:
            print("[Wensday] I didn't catch that. Try again.\n")
            continue

        lowered = spoken_text.lower().strip()

        # --- Wake Word Handling (multiple wake words) ---
        wake_word_used = None
        for w in WAKE_WORDS:
            if lowered.startswith(w):
                wake_word_used = w
                break

        if not wake_word_used:
            print("[Wensday] Wake word not detected — ignoring speech.\n")
            continue

        # Strip the wake word off the front
        command_text = lowered.replace(wake_word_used, "", 1).strip()

        # If user only said the wake word with nothing after it
        if not command_text:
            speak("Yes DJ?")
            continue

        # Step 3: Send the command to Wensday's brain (voice_mode=True for Jarvis style)
        answer = ask_wensday(command_text, voice_mode=True)

        # Step 4: Print and speak the answer
        print(f"[Wensday] {answer}\n")
        speak(answer)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[Wensday] Exiting voice loop.")
