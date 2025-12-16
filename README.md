# Projekt Wensday 🧠🎙️
A “Jarvis-style” **Python CLI assistant** that streams responses in real time and speaks them out loud with **ElevenLabs streaming TTS** — built as a hands-on **AI + automation** portfolio project for my cybersecurity journey.

> **Status:** Working prototype (streaming text + voice playback)  
> **Goal:** Evolve into a “Defensive Copilot” that helps explain alerts, summarize logs, and guide lab workflows (Wazuh / Suricata / cloud).

---

## What it does (today)
- Streams Wensday’s response to your terminal live (chunk-by-chunk)
- Converts the response into speech using ElevenLabs (streaming)
- Plays audio on macOS using `afplay`
- Uses a near-real-time pipeline:
  - **stream text → sentence chunking → queue → TTS worker → play audio**

---

## Tech stack
- Python 3.10+
- OpenAI (text generation / streaming)
- ElevenLabs (streaming text-to-speech)
- `requests` (HTTP streaming)
- macOS `afplay` (audio playback)

---

## Project structure
```txt
projekt-wensday/
├── src/
│   ├── wensday_cli.py
│   ├── wensday_llm.py
│   ├── wensday_voice.py
│   └── utils.py
├── docs/
│   ├── SETUP.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── USAGE.md
│   ├── TROUBLESHOOTING.md
│   └── SECURITY.md
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
