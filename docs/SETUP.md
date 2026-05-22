# Projekt Wensday Setup

This project is currently a Python prototype with CLI, voice, web, memory, and SOC-lab helper modules.

## Requirements

- Python 3.10+
- macOS for the current local audio playback helpers (`afplay` and `say`)
- OpenAI API key for assistant responses
- ElevenLabs API key for ElevenLabs voice output
- Optional: microphone access for push-to-talk voice scripts

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `sounddevice` install or microphone access fails on macOS, install PortAudio first:

```bash
brew install portaudio
```

## Configure

Create a local environment file from the example:

```bash
cp .env.example .env
```

Then fill in at least:

```bash
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

The app now loads `.env` automatically when `python-dotenv` is installed. You can still load it manually in your shell if needed:

```bash
set -a
source .env
set +a
```

## Minimal Smoke Check

After installing dependencies and configuring `.env`, run these checks from the repository root:

```bash
.venv/bin/python -m py_compile wensday_core/*.py *.py
```

Run the memory tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Audit events are written to `wensday_audit.jsonl` by default. This file is ignored by git.

```bash
.venv/bin/python - <<'PY'
from wensday_core.brain import build_prompt, categorize_message
print(categorize_message("show me the wazuh lab"))
print(build_prompt("hello")[:80])
PY
```

```bash
printf 'exit\n' | .venv/bin/python wensday_cli.py
```

```bash
.venv/bin/uvicorn wensday_web:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl http://127.0.0.1:8000/
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_text":"hello","voice_mode":false}'
```

## Run Options

Text brain prototype:

```bash
python test_wensday.py
```

CLI wrapper:

```bash
python wensday_cli.py
```

Web UI:

```bash
uvicorn wensday_web:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

Alternate API prototype:

```bash
uvicorn wensday_server:app --reload
```

SOC lab status:

```bash
python wensday_status.py
```

## Notes

- `wensday_core/brain.py` is now the stable import location for the existing `ask_wensday` text brain.
- Long-term memory is explicit. Use commands like `remember ...`, `forget ...`, `what do you remember`, and `search memory ...`.
- The older scripts are still present to preserve current behavior.
- Missing OpenAI or ElevenLabs keys should produce readable runtime messages instead of crashing during import.
