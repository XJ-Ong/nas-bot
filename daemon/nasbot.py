#!/usr/bin/env python3

import os
import sys
import time
import requests
import signal
import importlib.util
from dotenv import load_dotenv

# Load environment variables
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COMMANDS = {}


def send_reply(chat_id, text):
    """Sends a reply text message to a Telegram chat."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': chat_id, 'text': text}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending reply: {e}", flush=True)
        return False


def react_to_message(chat_id, message_id, emoji="👍"):
    """Reacts to a message with an emoji."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': [{'type': 'emoji', 'emoji': emoji}]
        }
        response = requests.post(url, json=data, timeout=10).json()
        if not response.get('ok'):
            print(f"Failed to react to message with {emoji}: {response}", flush=True)
        else:
            print(f"Reacted to message {message_id} with {emoji}", flush=True)

    except Exception as e:
        print(f"Error reacting to message: {e}", flush=True)


def load_commands():
    """Dynamically loads all command modules from the command/ directory."""
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
            # Flat file: command/hello.py → /hello
            module_name = entry[:-3]
            module_path = os.path.join(command_dir, entry)
        else:
            # One-level subdirectory: command/tmux/tmux.py → /tmux
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
    """Registers all loaded commands with Telegram's setMyCommands."""
    if not COMMANDS:
        return

    commands = []
    for name, mod in COMMANDS.items():
        cmd = getattr(mod, "COMMAND", name)
        help_text = getattr(mod, "HELP", "")
        commands.append({"command": cmd, "description": help_text[:128]})

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
        response = requests.post(url, json={"commands": commands}, timeout=10).json()
        if response.get("ok"):
            print(f"Registered {len(commands)} command(s) with Telegram", flush=True)
        else:
            print(f"Failed to register commands: {response}", flush=True)
    except Exception as e:
        print(f"Error registering commands: {e}", flush=True)


def process_command(message, text):
    """Routes a command message to the appropriate handler."""
    chat_id = message['chat']['id']
    message_id = message['message_id']

    parts = text.split()
    cmd = parts[0].lstrip("/").split("@")[0].lower()

    if cmd in COMMANDS:
        try:
            response = COMMANDS[cmd].run(message, BOT_TOKEN)
            if response:
                send_reply(chat_id, response)
            react_to_message(chat_id, message_id, "👍")
        except Exception as e:
            print(f"Error executing /{cmd}: {e}", flush=True)
    else:
        send_reply(chat_id, f"Unknown command: /{cmd}")


def process_message(message):
    """Processes an individual message."""
    chat_id = message['chat']['id']
    msg_chat_id = str(chat_id)
    if msg_chat_id != str(CHAT_ID):
        print(f"Ignored message from unauthorized chat: {msg_chat_id}", flush=True)
        return

    if 'text' in message:
        text = message['text']
        if text.startswith("/"):
            process_command(message, text)


def run_daemon():
    """Main loop for the Telegram listener."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN or CHAT_ID not set in .env")
        return

    print(f"Daemon started. Listening for Chat ID: {CHAT_ID}")
    env_path = os.path.join(SCRIPT_DIR, ".env")
    last_env_mtime = os.path.getmtime(env_path) if os.path.exists(env_path) else 0

    def restart_process():
        print("\n--- Restarting daemon... ---", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    signal.signal(signal.SIGHUP, lambda s, f: restart_process())

    load_commands()
    update_command_list()
    offset = 0

    while True:
        if os.path.exists(env_path):
            try:
                current_mtime = os.path.getmtime(env_path)
                if current_mtime > last_env_mtime:
                    print("\n--- .env change detected. ---", flush=True)
                    restart_process()
            except Exception:
                pass

        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {'offset': offset, 'timeout': 30}
            response = requests.get(url, params=params, timeout=35).json()

            if response.get('ok'):
                for update in response['result']:
                    if 'message' in update:
                        process_message(update['message'])
                    offset = update['update_id'] + 1
            else:
                print(f"Error from Telegram: {response}")
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopping daemon...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_daemon()