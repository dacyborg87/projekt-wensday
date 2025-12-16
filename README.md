# Projekt Wensday 🤖🎷  
A “Jarvis-style” CLI assistant that streams replies in real time and speaks them out loud using **ElevenLabs** TTS — built as a hands-on AI + automation project for my cybersecurity journey.  
  
> **Status:** Working (streaming text + voice playback)  
  
## What it does (today)  
- Streams Wensday’s response to your terminal **live** (token-by-token / chunk-by-chunk)  
- Converts the response into speech using **ElevenLabs streaming TTS**  
- Plays audio on macOS using `afplay`  
- Includes a near-real-time pipeline:  
  - stream text → split into sentence chunks → queue → background TTS worker → play  
  
## Tech stack  
- Python 3  
- OpenAI (text generation / streaming)  
- ElevenLabs (streaming text-to-speech)  
- `requests` (HTTP streaming)  
- macOS `afplay` (audio playback)  
  
## Project structure (recommended)  
```text  
projekt-wensday/  
├── wensday_cli.py  
├── wensday_voice.py  
├── README.md  
├── requirements.txt  
├── .env.example  
└── docs/  
    ├── SETUP.md  
    ├── ARCHITECTURE.md  
    └── ROADMAP.md  
```  
  
## Requirements  
- macOS (recommended) or any OS with an audio player you can swap in  
- Python 3.10+ (you can run newer versions too)  
- API keys:  
  - `OPENAI_API_KEY`  
  - `ELEVENLABS_API_KEY`  
  - `ELEVENLABS_VOICE_ID`  
  
## Quick start (macOS)  
### 1) Create & activate a virtual environment  
```bash  
python3 -m venv venv  
source venv/bin/activate  
```  
### 2) Install dependencies  
```bash  
pip install -r requirements.txt  
```  
### 3) Set environment variables (temporary for this terminal)  
```bash  
export OPENAI_API_KEY="YOUR_OPENAI_KEY"  
export ELEVENLABS_API_KEY="YOUR_ELEVENLABS_KEY"  
export ELEVENLABS_VOICE_ID="YOUR_VOICE_ID"  
```  
(Optional tuning)  
```bash  
export ELEVENLABS_STABILITY="0.35"  
export ELEVENLABS_SIMILARITY_BOOST="0.80"  
export ELEVENLABS_STYLE="0.35"  
```  
### 4) Run the CLI  
```bash  
python3 wensday_cli.py  
```  
Type `exit` to quit.  
  
## Notes  
- This project streams audio chunk-by-chunk, so you’ll hear Wensday speaking while the response is still being generated.  
- If you’re not on macOS, replace `afplay` with your OS audio command (see `docs/SETUP.md`).  
  
## Why I built this  
I’m building Projekt Wensday as a real portfolio project that combines:  
- AI assistant behavior  
- streaming UX  
- voice interfaces  
- automation patterns (queues, threads, chunking)  
- and a path toward a cybersecurity “copilot” for my labs (Wazuh, Suricata, etc.)  
  
## Roadmap  
Planned next:  
- Memory (short-term + long-term)  
- “Cyber Copilot” mode (log parsing, alert explanations, runbooks)  
- Config file for voices + settings  
- Optional UI layer (local dashboard)  
  
See `docs/ROADMAP.md`.  
  
## License  
Choose one (MIT recommended) once the repo is public. 
