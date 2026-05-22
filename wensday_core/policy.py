"""Defensive policy checks for Wensday OS.

Phase 4 is intentionally conservative: read-only defensive help is allowed,
clearly offensive cyber requests are blocked, and system-changing requests are
held for human approval instead of being executed.
"""

from dataclasses import dataclass
import re

from wensday_core.memory import contains_secret


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False


OFFENSIVE_PATTERNS = [
    r"\bexploit\b",
    r"\bmalware\b",
    r"\bransomware\b",
    r"\bkeylogger\b",
    r"\bcredential theft\b",
    r"\bsteal (?:password|token|cookie|credential)",
    r"\bbypass (?:edr|antivirus|av|detection)\b",
    r"\bevade (?:edr|antivirus|av|detection)\b",
    r"\bpersistence\b",
    r"\bprivilege escalation\b",
    r"\breverse shell\b",
    r"\bphishing kit\b",
    r"\bddos\b",
]

APPROVAL_PATTERNS = [
    r"\bdelete\b",
    r"\bdisable\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bkill\b",
    r"\bquarantine\b",
    r"\bisolate\b",
    r"\bblock\b",
    r"\bban\b",
    r"\bchange firewall\b",
    r"\bmodify\b",
    r"\bremove\b",
]

DEFENSIVE_CONTEXT = {
    "explain",
    "summarize",
    "triage",
    "detect",
    "detection",
    "defensive",
    "defense",
    "audit",
    "review",
    "hardening",
    "investigate",
    "incident",
    "wazuh",
    "suricata",
    "soc",
    "siem",
    "alert",
}


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _has_defensive_context(text: str) -> bool:
    tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
    return bool(tokens & DEFENSIVE_CONTEXT)


def evaluate_policy(user_input: str, request_type: str = "general_chat", mode: str = "personal") -> PolicyDecision:
    """Return the Phase 4 policy decision for a request."""
    text = user_input or ""

    if contains_secret(text):
        return PolicyDecision(
            allowed=False,
            reason="I cannot process or store secrets, tokens, passwords, API keys, or private keys.",
        )

    if _matches(OFFENSIVE_PATTERNS, text) and not _has_defensive_context(text):
        return PolicyDecision(
            allowed=False,
            reason="I can only help with defensive, authorized cybersecurity work.",
        )

    if _matches(APPROVAL_PATTERNS, text):
        return PolicyDecision(
            allowed=False,
            reason=(
                "That request could change system state. I can draft a defensive plan, "
                "but I will not execute system-changing actions without explicit human approval."
            ),
            requires_approval=True,
        )

    return PolicyDecision(allowed=True, reason="Allowed defensive/read-only request.")
