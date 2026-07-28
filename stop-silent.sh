#!/usr/bin/env bash
# AI Brief — stop silent background services on macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/temp/logs"
PID_FILE="$LOG_DIR/services.pids"

port_pids() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
}

kill_pid() {
  local pid="$1"
  [[ -z "${pid:-}" ]] && return 0
  if kill -0 "$pid" 2>/dev/null; then
    echo "  - killing PID $pid"
    kill "$pid" 2>/dev/null || true
    sleep 0.3
    kill -9 "$pid" 2>/dev/null || true
  fi
}

echo "[stop] Stopping tracked processes..."
if [[ -f "$PID_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$PID_FILE"
  kill_pid "${api_pid:-}"
  kill_pid "${bot_pid:-}"
else
  echo "  (no services.pids file)"
fi

if [[ -f "$ROOT/discord-bot/data/bot.pid" ]]; then
  bot_pid="$(tr -d '[:space:]' < "$ROOT/discord-bot/data/bot.pid" || true)"
  if [[ "$bot_pid" =~ ^[0-9]+$ ]]; then
    echo "[stop] Stopping bot.pid..."
    kill_pid "$bot_pid"
  fi
fi

echo "[stop] Cleaning listener ports 8900 / 8901..."
for port in 8900 8901; do
  for pid in $(port_pids "$port"); do
    echo "  - port $port PID $pid"
    kill_pid "$pid"
  done
done

# Child npm/node processes may remain after parent exit
pkill -f "$ROOT/discord-bot.*(ts-node|dist/index)" 2>/dev/null || true
pkill -f "$ROOT/.*aibrief\.api" 2>/dev/null || true

rm -f "$PID_FILE"
echo "[stop] Done."
