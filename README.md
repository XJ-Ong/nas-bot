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

# Install Python dependencies
pip3 install requests python-dotenv

# Run installer (creates config templates)
./install.sh
```

The installer creates:
- `~/.config/nas-bot/secrets` (bot token, chat ID, user whitelist)
- `daemon/command/diskcheck/.env` (from `.env.example` template)
- systemd service and timer units in `~/.config/systemd/user/`

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

Then configure the **disk check** command:

```bash
# Set your mount paths and thresholds
nano daemon/command/diskcheck/.env
```

See `daemon/command/diskcheck/README.md` for config format details.

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

# Start disk check timers
systemctl --user enable --now disk-check.timer
systemctl --user enable --now disk-check-daily.timer
```

### 7. Test

Message your bot in Telegram:
- `/diskcheck` — should reply immediately with disk usage

Check logs:

```bash
# Watch daemon logs live
journalctl --user -u nasbot.service -f

# Check timer execution
journalctl --user -u disk-check.service -n 20
```

## Structure

```
nas-bot/
├── lib.py                  # Shared Telegram/formatting helpers
├── install.sh              # Setup script (creates config + systemd units)
├── secrets.example         # Bot-level config template
└── daemon/
    ├── nasbot.py           # Telegram polling daemon (command dispatcher)
    └── command/
        └── diskcheck/      # Disk space monitoring
            ├── diskcheck.py
            ├── .env.example
            └── README.md
```

Each command under `daemon/command/` is self-contained with its own config and documentation. To add a new command, create a new folder following the same pattern — no changes needed to the daemon.

## Adding a New Command

1. Create `daemon/command/<name>/<name>.py` with:
   - `COMMAND = "name"`
   - `HELP = "Description for Telegram autocomplete"`
   - `def run(message: dict, bot_token: str) -> str:`
2. Create `daemon/command/<name>/.env.example` (config template)
3. Create `daemon/command/<name>/README.md` (usage docs)
4. Re-run `./install.sh` to bootstrap the `.env`
5. Restart the daemon: `systemctl --user restart nasbot.service`

The daemon auto-discovers and loads commands on startup.

## Requirements

- Python 3.7+
- `requests` and `python-dotenv` (via pip)
- systemd with `--user` support
- `loginctl enable-linger` enabled for the user

## License

See original [tg-tools](https://github.com/KOWX712/tg-tools) repository for base daemon licensing.
