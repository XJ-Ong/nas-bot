#!/usr/bin/env bash

# one-time setup script

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/nas-bot"
COMMAND_DIR="$REPO_DIR/daemon/command"
PYTHON_BIN="$(command -v python3)"

echo "Installing nas-bot from: $REPO_DIR"

mkdir -p "$SYSTEMD_USER_DIR" "$BIN_DIR" "$CONFIG_DIR"

# ── Bot-level secrets (BOT_TOKEN, CHAT_ID, ALLOWED_USER_IDS) ────────────
if [[ ! -f "$CONFIG_DIR/secrets" ]]; then
  cp "$REPO_DIR/secrets.example" "$CONFIG_DIR/secrets"
  chmod 600 "$CONFIG_DIR/secrets"
  echo ">>> Created $CONFIG_DIR/secrets from template — edit it with your real BOT_TOKEN and CHAT_ID before starting anything."
else
  echo "Secrets file already exists at $CONFIG_DIR/secrets — leaving it alone."
fi

# ── Per-command config (.env per command folder) ───────────────────────
if [[ -d "$COMMAND_DIR" ]]; then
  for cmd_dir in "$COMMAND_DIR"/*/; do
    [[ -f "$cmd_dir/.env.example" ]] || continue
    cmd_name=$(basename "$cmd_dir")
    if [[ ! -f "$cmd_dir/.env" ]]; then
      cp "$cmd_dir/.env.example" "$cmd_dir/.env"
      echo ">>> Created $cmd_dir.env from template — edit it for your system before this command will work (see $cmd_dir/README.md)."
    else
      echo "Config already exists at $cmd_dir.env — leaving it alone."
    fi
    chmod +x "$cmd_dir"/*.py 2>/dev/null || true
  done
fi

chmod +x "$REPO_DIR/daemon/nasbot.py"

# ── Symlink daemon for manual CLI use (optional convenience) ──────────
ln -sf "$REPO_DIR/daemon/nasbot.py" "$BIN_DIR/nasbot"

# ── Generate systemd --user units ──────────────────────────────────────

# disk-check: frequent silent check (every 30 min) — only pushes on breach.
cat > "$SYSTEMD_USER_DIR/disk-check.service" <<EOF
[Unit]
Description=Disk space check with Telegram alert (breach-only)

[Service]
Type=oneshot
ExecStart=$PYTHON_BIN $COMMAND_DIR/diskcheck/diskcheck.py --send
EOF

cat > "$SYSTEMD_USER_DIR/disk-check.timer" <<EOF
[Unit]
Description=Run diskcheck.py every 30 min, silent unless breached

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# disk-check: daily routine report, regardless of status.
cat > "$SYSTEMD_USER_DIR/disk-check-daily.service" <<EOF
[Unit]
Description=Daily disk status report (always sends)

[Service]
Type=oneshot
ExecStart=$PYTHON_BIN $COMMAND_DIR/diskcheck/diskcheck.py --send-always
EOF

cat > "$SYSTEMD_USER_DIR/disk-check-daily.timer" <<EOF
[Unit]
Description=Run diskcheck.py once daily, always reports

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# nasbot daemon (long-running, listens for Telegram commands)
cat > "$SYSTEMD_USER_DIR/nasbot.service" <<EOF
[Unit]
Description=nas-bot Telegram command listener
After=network.target

[Service]
ExecStart=$(command -v python3) $REPO_DIR/daemon/nasbot.py
WorkingDirectory=$REPO_DIR/daemon
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload

echo ""
echo "Install complete. Next steps:"
echo "  1. Edit bot secrets:   \$EDITOR $CONFIG_DIR/secrets"
echo "  2. Edit each command's config (created from .env.example wherever missing — see messages above)"
echo "  3. Enable lingering:   sudo loginctl enable-linger \$USER   (one-time, as root)"
echo "  4. Start everything:"
echo "       systemctl --user enable --now disk-check.timer"
echo "       systemctl --user enable --now disk-check-daily.timer"
echo "       systemctl --user enable --now nasbot.service"