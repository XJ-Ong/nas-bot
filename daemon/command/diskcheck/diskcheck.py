#!/usr/bin/env python3

# checks disk usage on configured mounts, reports via Telegram


import os
import sys
import shutil

COMMAND = "diskcheck"
HELP = "Check disk usage now"

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
sys.path.insert(0, REPO_ROOT)

import lib  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

CONFIG_FILE = os.path.join(SCRIPT_DIR, ".env")
if not os.path.exists(CONFIG_FILE):
    pass
load_dotenv(CONFIG_FILE)

HOSTNAME_LABEL = os.getenv("HOSTNAME_LABEL", "nas")


def _parse_mounts():
    """MOUNTS in .env can be multi-line or semicolon-separated."""
    raw = os.getenv("MOUNTS", "")
    entries = []
    for line in raw.replace(";", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            path, threshold, label = line.split(":", 2)
            entries.append((path.strip(), int(threshold.strip()), label.strip()))
        except ValueError:
            print(f"Skipping malformed MOUNTS entry: {line!r}", flush=True)
    return entries


def check_disks():
    """Runs the check."""
    mounts = _parse_mounts()
    if not mounts:
        return (
            f"⚠️ No MOUNTS configured in {CONFIG_FILE} — "
            f"copy .env.example to .env and edit it.",
            True,
        )

    report_lines = []
    any_breach = False

    for path, threshold, label in mounts:
        if not os.path.isdir(path):
            continue

        usage = shutil.disk_usage(path)
        used_pct = usage.used / usage.total * 100
        avail_gb = usage.free / (1024 ** 3)

        emoji = lib.status_emoji(used_pct, threshold)
        bar = lib.usage_bar(used_pct)

        # Escape label since it comes from user config
        safe_label = lib.escape_html(label)

        report_lines.append(
            f"{emoji} <b>{safe_label}</b>\n"
            f"   <code>{bar}</code> ({used_pct:.2f}%) · {avail_gb:.1f}G left"
        )

        if used_pct >= threshold:
            any_breach = True

    body = "\n\n".join(report_lines)
    message = lib.alert_header("disk space", any_breach, HOSTNAME_LABEL) + "\n" + body
    return message, any_breach


def run(message: dict, bot_token: str) -> str:
    """Called by the daemon"""
    text, _breach = check_disks()
    return text


if __name__ == "__main__":
    text, breached = check_disks()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--send":
        if breached:
            lib.send_telegram(text)
    elif mode == "--send-always":
        lib.send_telegram(text)
    else:
        print(text)
