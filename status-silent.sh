#!/usr/bin/env bash
# AI Brief — status of silent background services on macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/temp/logs"
PID_FILE="$LOG_DIR/services.pids"

port_pids() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
}

http_ok() {
  curl -fsS --max-time 2 "http://127.0.0.1:8900/health" >/dev/null 2>&1
}

tail_log() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "(no log file)"
    return
  fi
  tail -n 12 "$path" || true
}

echo "[status]"
if [[ -f "$PID_FILE" ]]; then
  echo "  Stored PIDs:"
  sed 's/^/    /' "$PID_FILE"
else
  echo "  Stored PIDs: (none)"
fi

if http_ok; then
  echo "  API health (8900): OK"
else
  echo "  API health (8900): DOWN"
fi

if [[ -n "$(port_pids 8901)" ]]; then
  echo "  Bot lock port (8901): LISTENING"
else
  echo "  Bot lock port (8901): DOWN"
fi

echo ""
echo "[api.err.log tail]"
tail_log "$LOG_DIR/api.err.log"
echo ""
echo "[bot.err.log tail]"
tail_log "$LOG_DIR/bot.err.log"
