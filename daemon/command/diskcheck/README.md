# /diskcheck

Checks disk usage on configured mounts and reports to Telegram.

## Config

Edit `.env` after running `install.sh`:

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

## Usage

- **On demand**: Message `/diskcheck` in Telegram
- **Scheduled**: Systemd timers call this automatically
  - `disk-check.timer` — Every 30 min, silent unless breached
  - `disk-check-daily.timer` — Daily at 8am, always reports

## Standalone Testing

```bash
# Print to stdout (no Telegram send)
python3 diskcheck.py

# Send only if threshold breached
python3 diskcheck.py --send

# Always send
python3 diskcheck.py --send-always
```
