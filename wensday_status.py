import subprocess
from typing import Dict


# 👉 CHANGE THESE to match your real lab IPs later
WAZUH_IP = "192.168.56.10"
WINDOWS_IP = "192.168.56.20"
KALI_IP = "192.168.56.30"


def ping_host(ip: str, count: int = 2) -> bool:
    """
    Ping a host a few times.
    Returns True if we get a reply, False if not.
    Works on macOS using the '-c' flag.
    """
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_status_report() -> str:
    """
    Build a simple text report about your lab machines.
    """
    systems: Dict[str, str] = {
        "Wazuh Manager": WAZUH_IP,
        "Windows VM": WINDOWS_IP,
        "Kali VM": KALI_IP,
    }

    lines = []
    lines.append("=== Home SOC Lab Status ===")

    for name, ip in systems.items():
        if ip.strip() == "":
            lines.append(f"- {name}: IP not set yet.")
            continue

        is_up = ping_host(ip)
        status = "UP ✅" if is_up else "DOWN ❌"
        lines.append(f"- {name} ({ip}): {status}")

    lines.append("")
    lines.append("Tip: Update the IPs in wensday_status.py to match your real VM addresses.")

    return "\n".join(lines)


if __name__ == "__main__":
    # So you can also run: python wensday_status.py
    print(get_status_report())