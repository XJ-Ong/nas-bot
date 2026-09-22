# shared, bot-level helpers for nas-bot.

import os
import requests
from dotenv import load_dotenv
from typing import Optional
import html

SECRETS_FILE = os.path.expanduser("~/.config/nas-bot/secrets")
load_dotenv(SECRETS_FILE)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ALLOWED_USER_IDS = {
    uid.strip() for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid.strip()
}


def send_telegram(text: str, chat_id: Optional[str] = None) -> bool:
    """Sends an HTML-formatted message to Telegram."""
    target = chat_id or CHAT_ID
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": target,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}", flush=True)
        return False


def react_to_message(chat_id, message_id, emoji: str = "👍") -> None:
    """Reacts to a message with an emoji."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": [{"type": "emoji", "emoji": emoji}],
        }
        response = requests.post(url, json=data, timeout=10).json()
        if not response.get("ok"):
            print(f"Failed to react to message with {emoji}: {response}", flush=True)
    except Exception as e:
        print(f"Error reacting to message: {e}", flush=True)


def usage_bar(pct: int, width: int = 10) -> str:
    """Simple block-character usage bar: [██████░░░░]"""
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def status_emoji(pct: int, threshold: int) -> str:
    """🔴 at/above threshold, 🟡 within 10 of it, 🟢 otherwise."""
    if pct >= threshold:
        return "🔴"
    elif pct >= threshold - 10:
        return "🟡"
    return "🟢"


def alert_header(title: str, breached: bool, hostname_label: str = "nas") -> str:
    """Standard message header every command reuses."""
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    icon = "⚠️" if breached else "✅"
    # Escape hostname_label since it comes from user config
    safe_hostname = html.escape(hostname_label)
    safe_title = html.escape(title)
    return f"{icon} <b>{safe_hostname} — {safe_title}</b>\n<i>{timestamp}</i>\n"


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent Telegram parse errors"""
    return html.escape(text)
