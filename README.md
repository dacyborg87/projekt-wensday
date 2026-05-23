# Wensday OS

Wensday OS is an AI-assisted defensive operations and personal command platform prototype. The project focuses on structured memory, controlled orchestration, explainable workflows, audit logging, policy guardrails, and future SOC-style cybersecurity tooling.



## Project Summary

Wensday OS is designed to become a private, user-centered assistant that helps with personal command workflows and defensive cybersecurity operations. The long-term direction is an analyst amplifier: a system that can help summarize alerts, organize investigations, explain evidence, retrieve relevant memory, and guide defensive workflows without becoming an autonomous offensive tool.

The project currently runs as a Python prototype with web, CLI, memory, voice, SOC-helper, policy, audit, plugin-placeholder, and orchestration components.

## Current Status

Status: educational prototype.

Current strengths:

- Centralized `ask_wensday()` compatibility path.
- Structured long-term memory with explicit save/search/forget commands.
- Controlled orchestration layer for request classification, policy checks, memory retrieval, read-only plugin routing, and audit hooks.
- FastAPI web interface prototype.
- CLI/voice-oriented scripts preserved for compatibility.
- Tests covering memory, policy, audit, plugins, and orchestration.

Not production-ready yet:

- No authentication or role-based access control.
- No production database.
- No encrypted memory/audit store.
- No tamper-evident audit trail.
- No active enterprise SIEM integration yet.
- Plugin system is intentionally read-only and minimal.

## Key Capabilities

- Personal AI assistant flow through `ask_wensday()`.
- Explicit long-term memory commands:
  - `remember ...`
  - `forget ...`
  - `what do you remember`
  - `search memory ...`
- Structured memory records with categories, tags, sensitivity, timestamps, and source.
- Basic secret filtering for API keys, tokens, passwords, and private keys.
- Request classification for general chat, memory commands, SOC-style requests, incident summaries, threat-intel requests, and planning/help requests.
- Defensive policy guardrails that block clearly offensive cyber requests before model calls.
- Human-approval placeholder responses for system-changing requests.
- Explainable prompt guidance for SOC, incident, threat-intel, and audit-style workflows.
- Local JSONL audit hooks with basic redaction.
- Read-only plugin registry placeholder for future defensive modules.

## Architecture Overview

Current high-level flow:

```text
Web / CLI / Voice Script
  -> wensday_core.brain.ask_wensday()
  -> WensdayOrchestrator
  -> request classification
  -> memory command handling
  -> policy guardrails
  -> read-only plugin routing
  -> relevant memory retrieval
  -> OpenAI response path
  -> audit event hooks
```

The orchestrator is defensive/read-only by default. It does not execute system-changing actions.

## Current Modules

```text
wensday_core/
├── audit.py          # Fail-soft JSONL audit logging with redaction
├── brain.py          # Backward-compatible ask_wensday() entrypoint
├── config.py         # OpenAI client/model configuration
├── memory.py         # Canonical structured memory system
├── orchestrator.py   # Controlled orchestration layer
├── personality.py    # Wensday system prompt/personality
├── plugins.py        # Read-only defensive plugin placeholders
├── policy.py         # Defensive policy guardrails
└── wensday.py        # Legacy duplicate memory helper; kept for now

static/
└── index.html        # Prototype web UI

tests/
├── test_audit.py
├── test_memory.py
├── test_orchestrator.py
├── test_plugins.py
└── test_policy.py
```

Other current scripts:

- `wensday_web.py`: FastAPI web app.
- `wensday_cli.py`: CLI interface.
- `wensday_voice.py`: ElevenLabs TTS helper.
- `wensday_talk.py`: experimental voice/chat loop.
- `wensday_server.py`: alternate API prototype.
- `wensday_soc.py`: early Wazuh alert-summary helper.
- `wensday_status.py`: basic lab status helper.
- `test_wensday.py`: legacy text/voice prototype entrypoint.

## Defensive/Security Principles

Wensday OS is intended for defensive, authorized, and educational workflows.

Core principles:

- Defensive/read-only by default.
- No offensive cyber capability.
- No malware, exploit, credential-theft, evasion, or unauthorized-access tooling.
- No autonomous system-changing actions.
- Human approval required before any future state-changing workflow.
- Explicit memory saves only.
- Basic secret filtering before memory saves.
- Audit metadata should avoid storing secrets or full private memory content.
- Outputs should separate facts, reasoning, confidence, next checks, and unverified assumptions where appropriate.

## Setup Instructions

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Set the values you need:

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.1
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

The app can import and run basic local checks without keys. Model and voice features require provider configuration.

## Running The Web App

Start the FastAPI web app:

```bash
.venv/bin/uvicorn wensday_web:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
```

The web app currently exposes:

- `GET /`
- `POST /chat`
- `POST /tts`

## Running Tests

Compile check:

```bash
.venv/bin/python -m py_compile wensday_core/*.py *.py tests/*.py
```

Unit tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

## Roadmap

Near-term:

- Keep stabilizing the orchestrator.
- Add safer SOC read-only plugin wrappers.
- Improve request classification.
- Improve explainable response formatting.
- Add incident summary data structures.
- Expand audit coverage.

Mid-term:

- Add Wazuh and Suricata read-only integrations.
- Add threat-intelligence enrichment such as CVE, CISA KEV, and MITRE ATT&CK references.
- Add role/mode-specific workflows for personal, SOC analyst, incident commander, auditor, and training modes.
- Add user review/approval queues for any future action workflow.

Long-term:

- Local/private deployment profile.
- Authentication and role-based access control.
- Encrypted memory/audit storage.
- Tamper-evident audit trail.
- Modular defensive plugin ecosystem.
- Optional local-model support.

## Disclaimer

Wensday OS is an educational prototype and portfolio project. It is defensive-focused and intended for authorized personal productivity, learning, lab, and SOC-style workflows. It is not production-ready, not a replacement for professional security tooling, and not designed for offensive cyber operations.
