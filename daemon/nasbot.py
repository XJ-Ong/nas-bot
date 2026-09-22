#!/usr/bin/env python3

# Telegram command listener. Forked from https://github.com/KOWX712/tg-tools (tgd.py).

import os
import sys
import time
import signal
import importlib.util
import requests

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)  # nas-bot/
sys.path.insert(0, REPO_ROOT)

import lib  # noqa: E402

COMMANDS = {}


def load_commands():
    """
    Dynamically loads all command modules from daemon/command/.
    Supports two layouts:
      - Flat file:   command/hello.py                -> /hello
      - Subfolder:   command/diskcheck/diskcheck.py  -> /diskcheck
    """
    global COMMANDS
    command_dir = os.path.join(SCRIPT_DIR, "command")
    if not os.path.isdir(command_dir):
        return

    for entry in sorted(os.listdir(command_dir)):
        if entry.startswith("_"):
            continue
        module_name = None
        module_path = None

        if entry.endswith(".py"):
            module_name = entry[:-3]
            module_path = os.path.join(command_dir, entry)
        else:
            subdir = os.path.join(command_dir, entry)
            if os.path.isdir(subdir):
                nested = os.path.join(subdir, f"{entry}.py")
                if os.path.isfile(nested):
                    module_name = entry
                    module_path = nested

        if module_name is None or module_path is None:
            continue

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "run"):
                COMMANDS[module_name] = module
                print(f"Loaded command: /{module_name}", flush=True)
        except Exception as e:
            print(f"Failed to load command '{module_name}': {e}", flush=True)


def update_command_list():
    """Registers all loaded commands with Telegram's setMyCommands (commands autocompletion)"""
    if not COMMANDS:
        return
    commands = []
    for name, mod in COMMANDS.items():
        cmd = getattr(mod, "COMMAND", name)
        help_text = getattr(mod, "HELP", "")
        commands.append({"command": cmd, "description": help_text[:128]})
    try:
        url = f"https://api.telegram.org/bot{lib.BOT_TOKEN}/setMyCommands"
        response = requests.post(url, json={"commands": commands}, timeout=10).json()
        if response.get("ok"):
            print(f"Registered {len(commands)} command(s) with Telegram", flush=True)
        else:
            print(f"Failed to register commands: {response}", flush=True)
    except Exception as e:
        print(f"Error registering commands: {e}", flush=True)


def process_command(message, text):
    """Routes a command message to the appropriate handler."""
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    parts = text.split()
    cmd = parts[0].lstrip("/").split("@")[0].lower()

    if cmd in COMMANDS:
        try:
            response = COMMANDS[cmd].run(message, lib.BOT_TOKEN)
            if response:
                lib.send_telegram(response, chat_id=chat_id)
            lib.react_to_message(chat_id, message_id, "👍")
        except Exception as e:
            print(f"Error executing /{cmd}: {e}", flush=True)
            lib.send_telegram(f"⚠️ /{cmd} failed: {e}", chat_id=chat_id)
    else:
        lib.send_telegram(f"Unknown command: /{cmd}", chat_id=chat_id)


def process_message(message):
    """Processes an individual message."""
    chat_id = message["chat"]["id"]
    if str(chat_id) != str(lib.CHAT_ID):
        print(f"Ignored message from unauthorized chat: {chat_id}", flush=True)
        return

    sender_id = str(message.get("from", {}).get("id", ""))
    if lib.ALLOWED_USER_IDS and sender_id not in lib.ALLOWED_USER_IDS:
        print(f"Ignored command from non-whitelisted user: {sender_id}", flush=True)
        return

    if "text" in message and message["text"].startswith("/"):
        process_command(message, message["text"])
    # Non-command text is ignored


def run_daemon():
    """Main loop for the Telegram listener."""
    if not lib.BOT_TOKEN or not lib.CHAT_ID:
        print(f"Error: BOT_TOKEN or CHAT_ID not set in {lib.SECRETS_FILE}")
        return

    print(f"nasbot daemon started. Listening for Chat ID: {lib.CHAT_ID}", flush=True)

    last_secrets_mtime = (
        os.path.getmtime(lib.SECRETS_FILE) if os.path.exists(lib.SECRETS_FILE) else 0
    )

    def restart_process(*_):
        print("\n--- Restarting daemon... ---", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    signal.signal(signal.SIGHUP, restart_process)

    load_commands()
    update_command_list()
    offset = 0

    while True:
        if os.path.exists(lib.SECRETS_FILE):
            try:
                current_mtime = os.path.getmtime(lib.SECRETS_FILE)
                if current_mtime > last_secrets_mtime:
                    print("\n--- secrets file changed, restarting ---", flush=True)
                    restart_process()
            except Exception:
                pass

        try:
            url = f"https://api.telegram.org/bot{lib.BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            response = requests.get(url, params=params, timeout=35).json()
            if response.get("ok"):
                for update in response["result"]:
                    if "message" in update:
                        process_message(update["message"])
                    offset = update["update_id"] + 1
            else:
                print(f"Error from Telegram: {response}", flush=True)
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}", flush=True)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopping daemon...", flush=True)
            break
        except Exception as e:
            print(f"Unexpected error: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    run_daemon()
