# nas-bot

A self-hosted NAS monitoring tool that reports to Telegram.

Forked from [KOWX712/tg-tools](https://github.com/KOWX712/tg-tools) — original daemon architecture by KOWX712.

## Features

- **Scheduled checks**: Frequent silent monitoring (alerts only on threshold breach) plus daily status reports
- **On-demand checks**: Message `/diskcheck` anytime for immediate status
- **User-level service**: Runs via `systemd --user` — no root needed, no Docker, no privileged daemon

## Commands

- `/diskcheck` — Check disk usage on configured mounts

Each command is self-contained under `daemon/command/<name>/` with its own config, logic, and README.

## Installation

### 1. Prerequisites

- **Python 3** with pip
- **systemd** with user service support
- A **Telegram bot token** from [@BotFather](https://t.me/BotFather)

### 2. Create Your Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Save the bot token (looks like `123456789:AAExampleTokenHere`)
4. Add the bot to your target chat/group
5. Get your chat ID:
   - Send a message in the chat
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `"chat":{"id":-987654321,...}` — note the number (negative for groups)
6. Get your user ID (for command whitelist):
   - Message [@userinfobot](https://t.me/userinfobot) to get your numeric user ID

### 3. Clone and Install

```bash
git clone https://github.com/XJ-Ong/nas-bot.git
cd nas-bot

# Create an isolated virtual environment for this project's dependencies
python3 -m venv venv
source venv/bin/activate
pip install requests python-dotenv
deactivate

# Run installer (creates config templates and systemd units)
./install.sh
```

**Note**: If needed, give the install script execute permission by running `chmod +x install.sh`

The installer:
- Creates `~/.config/nas-bot/secrets` from `secrets.example` (bot token, chat ID, user whitelist)
- Creates `.env` files from each command's `.env.example` template (if not already present)
- **Dynamically generates** systemd service and timer units for every commands in `daemon/command/` in `~/.config/systemd/user/`

### 4. Configure

Edit the bot-level secrets file:

```bash
nano ~/.config/nas-bot/secrets
```

Set your bot token, chat ID, and allowed user IDs:

```bash
BOT_TOKEN="123456789:AAExampleTokenFromBotFather"
CHAT_ID="-987654321"
ALLOWED_USER_IDS="111111111,222222222"
```

Then configure each command's specific settings:

```bash
nano daemon/command/diskcheck/.env
```

Each command's `.env.example` should document its configuration options and timer schedules.

**Note:** Timer/schedule values (`TIMER_*`, `RUN_MODE`, `ENTRY_SCRIPT`) are baked into the generated systemd units at install time. After changing them, re-run `./install.sh` to regenerate the units. Runtime-only values (e.g. `MOUNTS`) and bot secrets are read live — no re-run needed.

### 5. Enable Lingering (one-time, requires sudo)

This keeps user services running after logout:

```bash
sudo loginctl enable-linger $USER
```

Verify:

```bash
loginctl show-user $USER | grep Linger
# Should show: Linger=yes
```

### 6. Start Services

```bash
# Start the Telegram daemon
systemctl --user enable --now nasbot.service

# List all timer units
systemctl --user list-unit-files | grep nas-bot

# Enable disk check timers (for diskcheck command)
systemctl --user enable --now diskcheck.timer
systemctl --user enable --now diskcheck-secondary.timer
```

### 7. Test

Message your bot in Telegram:
- `/diskcheck` — should reply immediately with disk usage

Check logs:

```bash
# Watch daemon logs live
journalctl --user -u nasbot.service -f

# Check timer execution
journalctl --user -u diskcheck.service -n 20
```

## Structure

```
nas-bot/
├── venv/                     # Python virtual environment (created locally)
├── lib.py                    # Shared Telegram/formatting helpers
├── install.sh                # Dynamic setup script (discovers commands, generates systemd units)
├── secrets.example           # Bot-level config template
└── daemon/
    ├── nasbot.py             # Telegram polling daemon (command dispatcher)
    └── command/
        └── diskcheck/        # Disk space monitoring
            ├── diskcheck.py
            ├── .env.example  # Declares timer schedules + command config
            └── README.md
```

Each command under `daemon/command/` is self-contained with its own config and documentation. The installer dynamically discovers every command directory and generates its systemd units based on timer configuration in its `.env`.

## Adding a New Command

1. Create `daemon/command/<name>/<name>.py` with:
   - `COMMAND = "name"`
   - `HELP = "Description for Telegram autocomplete"`
   - `def run(message: dict, bot_token: str) -> str:`
2. Create `daemon/command/<name>/.env.example` with:
   - Timer schedule variables (`TIMER_INTERVAL` or `TIMER_CALENDAR`)
   - Command-specific configuration (paths, thresholds, etc.)
   - See `daemon/command/diskcheck/.env.example` for reference
3. Create `daemon/command/<name>/README.md` (usage docs)
4. Add a `.env` for it (copy from `.env.example`, or `install.sh` will create one on next run)
5. Re-run `./install.sh` to generate systemd units
6. Restart the daemon: `systemctl --user restart nasbot.service`

The daemon auto-discovers and loads commands on startup. The installer auto-generates timer units from each command's `.env` configuration.

### Custom Commands
Any command directory under `daemon/command/` gets installed as long as it has a `.env` — whether or not it's committed to git.

If you want a personal/experimental command to stay off GitHub, keep its directory untracked from git:

```bash
cd <path-of-custom-command>
echo "*" > .gitignore
```

## Requirements

- Python 3.7+ with `venv` module (`python3-venv` or `python3-full`)
- `requests` and `python-dotenv` (installed into the local venv)
- systemd with `--user` support
- `loginctl enable-linger` enabled for the user