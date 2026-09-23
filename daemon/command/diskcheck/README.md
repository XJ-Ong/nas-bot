# /diskcheck

Checks disk usage on configured mounts and reports to Telegram.

## Config

The `install.sh` script automatically creates `.env` from `.env.example` if it doesn't exist. Edit it to configure your mount points and schedule:

```bash
nano daemon/command/diskcheck/.env
```

### Mount Configuration

```bash
# One mount per line: "path:threshold:label"
MOUNTS="
/:80:Root
/home:85:Home
/mnt/data:90:Bulk Storage
"

HOSTNAME_LABEL="nas"
```

- `path` — Directory to check (reports usage of the filesystem it's on)
- `threshold` — 0-100, alert fires at or above this percentage
- `label` — Display name in the Telegram message

Add or remove lines as needed for your system.

### Timer Schedule Configuration

The installer reads these variables from `.env` to generate systemd timer units:

```bash
# Primary: frequent silent check, alerts only on breach
TIMER_INTERVAL=30min
TIMER_ON_BOOT=5min
RUN_MODE=--send

# Secondary: daily report regardless of status
TIMER_CALENDAR_SECONDARY="*-*-* 08:00:00"
RUN_MODE_SECONDARY=--send-always
```

After editing `.env`, re-run `./install.sh` to regenerate the timer units with your new schedule.

## Usage

- **On demand**: Message `/diskcheck` in Telegram
- **Scheduled**: Systemd timers call this automatically
  - `diskcheck.timer` — Every 30 min, silent unless breached
  - `diskcheck-secondary.timer` — Daily at 8am, always reports

## Standalone Testing

```bash
# Print to stdout (no Telegram send)
python3 diskcheck.py

# Send only if threshold breached
python3 diskcheck.py --send

# Always send
python3 diskcheck.py --send-always
```
