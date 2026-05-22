"""Controlled orchestration layer for Wensday OS."""

from dataclasses import dataclass, field
import re

from wensday_core.audit import write_audit_event
from wensday_core.config import get_model_name, get_openai_client
from wensday_core.memory import format_memories_for_prompt, get_relevant_memories
from wensday_core.plugins import PluginRegistry, build_default_registry
from wensday_core.policy import PolicyDecision, evaluate_policy


@dataclass
class WensdayRequest:
    user_input: str
    voice_mode: bool = False
    mode: str = "personal"
    request_type: str = "general_chat"


@dataclass
class WensdayResponse:
    answer: str
    request_type: str
    mode: str
    confidence: str = "medium"
    evidence: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    requires_approval: bool = False

    def to_text(self) -> str:
        return self.answer


REQUEST_KEYWORDS = {
    "soc_summary": {"wazuh", "suricata", "soc", "siem", "alert", "alerts", "ids"},
    "lab_status": {"status", "ping", "host", "vm", "online", "offline"},
    "incident_summary": {"incident", "timeline", "forensics", "containment", "eradication"},
    "threat_intel": {"cve", "ioc", "threat", "mitre", "kev", "ttp"},
    "project_planning": {"project", "roadmap", "plan", "milestone"},
    "learning_help": {"learn", "study", "homework", "class", "explain"},
}

MODE_INSTRUCTIONS = {
    "personal": "Personal assistant mode: be clear, useful, and concise.",
    "soc_analyst": (
        "SOC analyst mode: defensive/read-only by default. Separate facts, evidence, "
        "reasoning, confidence, and recommended next checks."
    ),
    "incident_commander": (
        "Incident commander mode: summarize timeline, affected assets, decisions needed, "
        "confidence, and unverified assumptions."
    ),
    "auditor": "Auditor mode: read-only, evidence-focused, and explicit about what was not verified.",
    "training": "Training mode: defensive lab-safe education only. Do not provide offensive instructions.",
    "read_only": "Read-only mode: do not perform or suggest autonomous system-changing actions.",
}


def classify_request(user_input: str) -> str:
    """Classify a request with deterministic Phase 4 keyword matching."""
    lower = (user_input or "").lower().strip()
    if lower.startswith(("remember ", "forget ", "search memory ")) or lower in {
        "what do you remember",
        "what do you remember?",
        "show memories",
        "list memories",
    }:
        return "memory_command"

    tokens = set(re.findall(r"[a-z0-9_]+", lower))
    for request_type, keywords in REQUEST_KEYWORDS.items():
        if tokens & keywords:
            return request_type
    return "general_chat"


def mode_for_request(request_type: str, requested_mode: str = "personal") -> str:
    """Resolve a safe mode while preserving default behavior."""
    if requested_mode and requested_mode in MODE_INSTRUCTIONS:
        return requested_mode
    if request_type in {"soc_summary", "threat_intel"}:
        return "soc_analyst"
    if request_type == "incident_summary":
        return "incident_commander"
    return "personal"


def _format_explainability_block(request_type: str, mode: str) -> str:
    if request_type in {"soc_summary", "incident_summary", "threat_intel"} or mode in {
        "soc_analyst",
        "incident_commander",
        "auditor",
    }:
        return (
            "Use this defensive explainable format when it fits:\n"
            "Summary:\n"
            "Evidence:\n"
            "Reasoning:\n"
            "Confidence:\n"
            "Recommended next checks:\n"
            "What I did not verify:\n\n"
        )
    return ""


class WensdayOrchestrator:
    """Controlled Phase 4 orchestration shell around the existing Wensday brain."""

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self.plugin_registry = plugin_registry or build_default_registry()

    def handle(self, user_input: str, voice_mode: bool = False, mode: str = "personal") -> str:
        request_type = classify_request(user_input)
        resolved_mode = mode_for_request(request_type, mode)
        request = WensdayRequest(
            user_input=user_input,
            voice_mode=voice_mode,
            mode=resolved_mode,
            request_type=request_type,
        )
        return self.process(request).to_text()

    def process(self, request: WensdayRequest) -> WensdayResponse:
        write_audit_event(
            "request_received",
            {
                "request_type": request.request_type,
                "mode": request.mode,
                "voice_mode": request.voice_mode,
            },
        )

        memory_response = self.handle_memory_command(request)
        if memory_response is not None:
            write_audit_event(
                "memory_command",
                {
                    "request_type": request.request_type,
                    "mode": request.mode,
                },
            )
            return memory_response

        policy = evaluate_policy(request.user_input, request.request_type, request.mode)
        if not policy.allowed:
            write_audit_event(
                "policy_denied",
                {
                    "request_type": request.request_type,
                    "mode": request.mode,
                    "requires_approval": policy.requires_approval,
                    "reason": policy.reason,
                },
            )
            return self._policy_response(request, policy)

        plugin_result = self.plugin_registry.route(request)
        if plugin_result.handled:
            write_audit_event(
                "plugin_used",
                {
                    "request_type": request.request_type,
                    "mode": request.mode,
                    "plugin": plugin_result.plugin_name,
                    "evidence_count": len(plugin_result.evidence),
                },
            )
            return WensdayResponse(
                answer=plugin_result.answer,
                request_type=request.request_type,
                mode=request.mode,
                confidence=plugin_result.confidence,
                evidence=plugin_result.evidence,
            )

        memories = get_relevant_memories(request.user_input, limit=5)
        write_audit_event(
            "memory_retrieved",
            {
                "request_type": request.request_type,
                "mode": request.mode,
                "memory_count": len(memories),
                "memory_categories": [memory.get("category", "general") for memory in memories],
            },
        )

        prompt = self.build_prompt(request, memories)
        answer = self.call_model(prompt)
        write_audit_event(
            "request_completed",
            {
                "request_type": request.request_type,
                "mode": request.mode,
                "policy_allowed": True,
                "requires_approval": False,
            },
        )
        return WensdayResponse(answer=answer, request_type=request.request_type, mode=request.mode)

    def handle_memory_command(self, request: WensdayRequest) -> WensdayResponse | None:
        if request.request_type != "memory_command":
            return None
        from wensday_core.brain import handle_memory_command

        answer = handle_memory_command(request.user_input)
        if answer is None:
            return None
        return WensdayResponse(answer=answer, request_type=request.request_type, mode=request.mode)

    def build_prompt(self, request: WensdayRequest, memories: list[dict]) -> str:
        # Import here to avoid a module-level cycle with brain.py.
        from wensday_core.brain import build_prompt

        prompt = build_prompt(request.user_input, voice_mode=request.voice_mode)
        mode_text = MODE_INSTRUCTIONS.get(request.mode, MODE_INSTRUCTIONS["personal"])
        memory_text = ""
        if memories:
            memory_text = "[RELEVANT MEMORY]\n" + format_memories_for_prompt(memories) + "\n\n"
        return (
            "[WENSDAY ORCHESTRATOR]\n"
            f"Request type: {request.request_type}\n"
            f"Mode: {request.mode}\n"
            f"Mode rules: {mode_text}\n"
            "Core principle: Wensday is an analyst amplifier and personal assistant, not an autonomous offensive tool.\n"
            "Default posture: defensive/read-only. Do not claim to execute system-changing actions.\n\n"
            + _format_explainability_block(request.request_type, request.mode)
            + memory_text
            + prompt
        )

    def call_model(self, prompt: str) -> str:
        try:
            client = get_openai_client()
        except RuntimeError as exc:
            return f"Wensday is not fully configured yet: {exc}"

        try:
            response = client.responses.create(model=get_model_name(), input=prompt)
        except Exception as exc:
            return f"Wensday could not reach OpenAI right now: {exc}"
        return response.output_text

    def _policy_response(self, request: WensdayRequest, policy: PolicyDecision) -> WensdayResponse:
        return WensdayResponse(
            answer=policy.reason,
            request_type=request.request_type,
            mode=request.mode,
            confidence="high",
            requires_approval=policy.requires_approval,
        )
