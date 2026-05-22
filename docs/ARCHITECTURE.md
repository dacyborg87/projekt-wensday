# Projekt Wensday Architecture

Projekt Wensday is a working prototype for a personal AI assistant with text, voice, web, memory, and SOC-lab capabilities.

## Current Layout

```text
.
├── wensday_core/
│   ├── brain.py
│   ├── config.py
│   ├── memory.py
│   ├── personality.py
│   └── wensday.py
├── static/
│   ├── index.html
│   └── wensday-logo.png
├── docs/
│   ├── ARCHITECTURE.md
│   └── SETUP.md
├── test_wensday.py
├── wensday_cli.py
├── wensday_server.py
├── wensday_soc.py
├── wensday_status.py
├── wensday_talk.py
├── wensday_voice.py
├── wensday_web.py
├── requirements.txt
└── .env.example
```

## Core Systems

### Orchestrator

`wensday_core/orchestrator.py` is the controlled Phase 4 orchestration layer. Existing interfaces still call `ask_wensday()`, but `ask_wensday()` now delegates to `WensdayOrchestrator` for request classification, defensive policy checks, memory retrieval, read-only plugin routing, explainable prompt context, audit hooks, and approval placeholders.

The orchestrator is defensive/read-only by default. It does not execute system-changing actions.

### Policy

`wensday_core/policy.py` contains conservative guardrails. It blocks clearly offensive cyber requests before OpenAI and returns an approval-required message for requests that could change system state.

### Audit

`wensday_core/audit.py` writes minimal JSONL audit events to `wensday_audit.jsonl` by default. Audit logging is fail-soft and redacts obvious secrets. It records request metadata such as request type, mode, memory count, plugin name, and policy decisions, not full private memory content.

### Plugins

`wensday_core/plugins.py` defines a read-only defensive plugin placeholder interface. Phase 4 plugins must be read-only. Future phases can wrap SOC helpers such as Wazuh summaries, lab status checks, Suricata log readers, incident summaries, and threat-intel enrichment.

### Brain

`wensday_core/brain.py` remains the stable compatibility import location for:

- `categorize_message`
- `build_prompt`
- `ask_wensday`

It keeps legacy helpers available, while `ask_wensday()` delegates to `WensdayOrchestrator`.

### Personality

`wensday_core/personality.py` contains the main Wensday system prompt and voice-mode behavior rules.

### Memory

`wensday_core/memory.py` stores long-term memories in a local JSON file named `wensday_memory.json` by default. It is the canonical memory module.

New memories use a structured JSON shape:

- `id`
- `category`
- `title`
- `content`
- `tags`
- `sensitivity`
- `created_at`
- `updated_at`
- `source`

Older `text/category/timestamp` memories still load through a compatibility normalization path.

Memory is explicit in the current stabilization phase. Wensday no longer saves every user message and assistant reply automatically. The brain handles these commands before calling OpenAI:

- `remember ...`
- `forget ...`
- `what do you remember`
- `search memory ...`

The orchestrator retrieves relevant memories with simple keyword and category scoring through `get_relevant_memories(user_input, limit=5)`. Vector search and embeddings are intentionally not part of this phase.

`wensday_core/wensday.py` currently duplicates memory behavior and should be consolidated later.

### Voice

`wensday_voice.py` handles ElevenLabs text-to-speech for generated text and plays audio with macOS `afplay`.

`test_wensday.py` also contains an experimental push-to-talk voice loop using OpenAI transcription, `sounddevice`, and macOS `say`.

`wensday_talk.py` contains another experimental voice/chat loop with mode and memory augmentation.

### Web

`wensday_web.py` is the main FastAPI web prototype. It serves:

- `GET /`
- `POST /chat`
- `POST /tts`

The browser UI lives in `static/index.html` and includes text chat, browser speech recognition, local speech synthesis, and optional ElevenLabs TTS.

`wensday_server.py` is an alternate API prototype for `test_ui.html`.

### SOC

`wensday_soc.py` summarizes Wazuh alert JSON logs.

`wensday_status.py` pings hardcoded SOC lab IPs and prints a status report.

## Current Execution Flow

### Web Chat

```text
static/index.html
  -> POST /chat
  -> wensday_web.chat_endpoint
  -> wensday_core.brain.ask_wensday
  -> OpenAI Responses API
  -> explicit memory commands may call wensday_core.memory.add_memory
  -> JSON reply
```

### Web TTS

```text
static/index.html
  -> POST /tts
  -> wensday_web.tts_endpoint
  -> ElevenLabs API
  -> browser plays MP3 response
```

### Legacy Text Brain

```text
python test_wensday.py
  -> ask_wensday from wensday_core.brain
  -> OpenAI
  -> memory JSON
```

### SOC Status

```text
python wensday_status.py
  -> ping configured lab IPs
  -> print report
```

## Stabilization Direction

The smallest immediate stabilization is to keep existing scripts while centralizing shared behavior:

- Keep `wensday_core/brain.py` as the canonical assistant brain.
- Keep `wensday_core/memory.py` as the canonical memory helper.
- Keep `wensday_web.py` as the preferred web app.
- Keep `wensday_voice.py` focused on TTS/playback.
- Gradually retire duplicate or experimental logic after tests exist.

Future phases should introduce centralized settings, cleaner module boundaries, tests, and a plugin-style module registry without breaking the current scripts.
