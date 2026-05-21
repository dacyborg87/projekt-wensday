import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# 👉 IMPORTANT:
# Change this path later if your Wazuh alerts file is in a different place.
WAZUH_ALERTS_PATH = Path("/var/ossec/logs/alerts/alerts.json")


def load_wazuh_alerts(limit: int = 500):
    """
    Load the most recent Wazuh alerts from a JSON-lines file.
    If the file doesn't exist or can't be read, return an empty list.
    """
    alerts = []

    if not WAZUH_ALERTS_PATH.exists():
        return alerts

    try:
        with WAZUH_ALERTS_PATH.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    alert = json.loads(line)
                    alerts.append(alert)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    # Keep only the last N alerts
    return alerts[-limit:]


def get_lab_summary(hours: int = 24) -> str:
    """
    Build a simple text summary of Wazuh alerts from the last N hours.
    This is what Wensday will read back to you.
    """
    alerts = load_wazuh_alerts()
    if not alerts:
        return (
            "I couldn't find any Wazuh alerts to summarize yet. "
            "We might need to double-check the alerts file path or generate some test activity."
        )

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    recent_alerts = []
    for alert in alerts:
        # Try a few possible timestamp locations
        ts_str = (
            alert.get("timestamp")
            or alert.get("event", {}).get("timestamp")
            or alert.get("@timestamp")
        )
        if not ts_str:
            continue

        # Make sure we can parse the timestamp
        try:
            # Handle "2025-12-01T10:20:30Z" style strings
            ts_str_clean = ts_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str_clean)
        except Exception:
            continue

        if ts >= cutoff:
            recent_alerts.append(alert)

    if not recent_alerts:
        return (
            f"In the last {hours} hours, I didn't see any recent alerts in the Wazuh log. "
            "The lab might be quiet, or the timestamps may not match what I'm expecting yet."
        )

    # Count by rule description, source IP, and severity level
    rule_counts = Counter()
    srcip_counts = Counter()
    severity_counts = Counter()

    for alert in recent_alerts:
        rule = alert.get("rule", {})
        rule_name = rule.get("description") or f"Rule {rule.get('id', 'unknown')}"
        rule_counts[rule_name] += 1

        srcip = (
            alert.get("data", {}).get("srcip")
            or alert.get("agent", {}).get("ip")
            or "unknown"
        )
        srcip_counts[srcip] += 1

        level = str(rule.get("level", "unknown"))
        severity_counts[level] += 1

    # Build a human-readable summary string
    lines = []
    lines.append(f"Here is your lab summary for the last {hours} hours:")
    lines.append(f"- Total alerts: {len(recent_alerts)}")

    lines.append("- Top rules:")
    for name, count in rule_counts.most_common(5):
        lines.append(f"  • {name}: {count} alerts")

    lines.append("- Top source IPs:")
    for ip, count in srcip_counts.most_common(5):
        lines.append(f"  • {ip}: {count} alerts")

    lines.append("- Severity levels:")
    for level, count in severity_counts.items():
        lines.append(f"  • Level {level}: {count} alerts")

    return "\n".join(lines)