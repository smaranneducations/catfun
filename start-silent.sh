#!/usr/bin/env bash
# AI Brief — silent start on macOS (API :8900 + Discord bot lock :8901)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/temp/logs"
mkdir -p "$LOG_DIR" "$ROOT/discord-bot/data"

API_OUT="$LOG_DIR/api.out.log"
API_ERR="$LOG_DIR/api.err.log"
BOT_OUT="$LOG_DIR/bot.out.log"
BOT_ERR="$LOG_DIR/bot.err.log"
PID_FILE="$LOG_DIR/services.pids"
STATUS_FILE="$LOG_DIR/start-silent.status.txt"

# Avoid Cursor/npm host env leaking into the bot process
unset npm_config_devdir || true

# Prefer project venv (Python 3.12+), then Homebrew python3.12, then system python3
PYTHON_BIN="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  if [[ -x /opt/homebrew/bin/python3.12 ]]; then
    PYTHON_BIN="/opt/homebrew/bin/python3.12"
  elif [[ -x "$ROOT/venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

# Prefer shared local-node runtime (Projects/local-node)
LOCAL_NODE_BIN="$(cd "$ROOT/.." && pwd)/local-node/bin"
if [[ -x "$LOCAL_NODE_BIN/node" ]]; then
  export PATH="$LOCAL_NODE_BIN:$PATH"
fi

if [[ ! -f "$ROOT/aibrief/api.py" ]]; then
  echo "[error] aibrief/api.py not found"
  exit 1
fi
if [[ ! -f "$ROOT/discord-bot/package.json" ]]; then
  echo "[error] discord-bot/package.json not found"
  exit 1
fi

# Prefer compiled bot for silent runs (faster / more reliable than ts-node)
BOT_ENTRY="$ROOT/discord-bot/dist/index.js"
if [[ ! -f "$BOT_ENTRY" ]]; then
  echo "[start] Building discord-bot (dist missing)..."
  (cd "$ROOT/discord-bot" && npm run build)
fi
if [[ ! -f "$BOT_ENTRY" ]]; then
  echo "[error] discord-bot/dist/index.js not found — run: cd discord-bot && npm run build"
  exit 1
fi

port_pids() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true
}

kill_pid() {
  local pid="$1"
  [[ -z "${pid:-}" ]] && return 0
  kill "$pid" 2>/dev/null || true
  sleep 0.2
  kill -9 "$pid" 2>/dev/null || true
}

kill_ports() {
  local port pid
  for port in 8900 8901; do
    for pid in $(port_pids "$port"); do
      echo "[cleanup] Port $port -> killing PID $pid"
      kill_pid "$pid"
    done
  done

  if [[ -f "$ROOT/discord-bot/data/bot.pid" ]]; then
    local bot_pid
    bot_pid="$(tr -d '[:space:]' < "$ROOT/discord-bot/data/bot.pid" || true)"
    if [[ "$bot_pid" =~ ^[0-9]+$ ]]; then
      kill_pid "$bot_pid"
    fi
  fi

  if [[ -f "$PID_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$PID_FILE" 2>/dev/null || true
    kill_pid "${api_pid:-}"
    kill_pid "${bot_pid:-}"
  fi
}

http_ok() {
  curl -fsS --max-time 2 "http://127.0.0.1:8900/health" >/dev/null 2>&1
}

port_listening() {
  local port="$1"
  [[ -n "$(port_pids "$port")" ]]
}

echo "[start] Cleaning old listeners..."
kill_ports
sleep 1

# Truncate local log copies
: >"$API_OUT"
: >"$API_ERR"
: >"$BOT_OUT"
: >"$BOT_ERR"

echo "[start] Launching API + Discord bot in background..."

# Spawn in a new session so closing Cursor/terminal does not kill services
NODE_BIN="$(command -v node)"
read -r API_PID BOT_PID < <(
  PYTHON_BIN="$PYTHON_BIN" NODE_BIN="$NODE_BIN" BOT_ENTRY="$BOT_ENTRY" \
  API_OUT="$API_OUT" API_ERR="$API_ERR" BOT_OUT="$BOT_OUT" BOT_ERR="$BOT_ERR" \
  ROOT="$ROOT" python3 - <<'PY'
import os, subprocess
from pathlib import Path

root = Path(os.environ["ROOT"])
os.chdir(root)

api = subprocess.Popen(
    [os.environ["PYTHON_BIN"], "-u", "-m", "aibrief.api", "--port", "8900"],
    stdout=open(os.environ["API_OUT"], "ab", buffering=0),
    stderr=open(os.environ["API_ERR"], "ab", buffering=0),
    stdin=subprocess.DEVNULL,
    start_new_session=True,
    cwd=str(root),
)
bot = subprocess.Popen(
    [os.environ["NODE_BIN"], os.environ["BOT_ENTRY"]],
    stdout=open(os.environ["BOT_OUT"], "ab", buffering=0),
    stderr=open(os.environ["BOT_ERR"], "ab", buffering=0),
    stdin=subprocess.DEVNULL,
    start_new_session=True,
    cwd=str(root),
)
print(api.pid, bot.pid)
PY
)

{
  echo "api_pid=$API_PID"
  echo "bot_pid=$BOT_PID"
} >"$PID_FILE"

echo "[start] API PID: $API_PID"
echo "[start] BOT PID: $BOT_PID"

api_ok=0
bot_ok=0
for _ in $(seq 1 60); do
  sleep 1
  if http_ok; then api_ok=1; fi
  if port_listening 8901; then bot_ok=1; fi
  if [[ "$api_ok" -eq 1 && "$bot_ok" -eq 1 ]]; then
    break
  fi
done

{
  echo "Completed at: $(date)"
  echo "API PID: $API_PID"
  echo "BOT PID: $BOT_PID"
  echo "API healthy: $api_ok"
  echo "Bot lock port 8901 listening: $bot_ok"
} >"$STATUS_FILE"

echo ""
echo "[status]"
if [[ "$api_ok" -eq 1 ]]; then
  echo "  API health (8900): OK"
else
  echo "  API health (8900): NOT READY"
fi
if [[ "$bot_ok" -eq 1 ]]; then
  echo "  Bot lock port (8901): LISTENING"
else
  echo "  Bot lock port (8901): NOT READY"
fi
echo ""
echo "Logs: $LOG_DIR"
echo "Stop with:  ./stop-silent.sh"
echo "Status:     ./status-silent.sh"

if [[ "$api_ok" -eq 1 && "$bot_ok" -eq 1 ]]; then
  echo "Done. Services are running silently in the background."
  exit 0
fi
echo "[warn] Startup incomplete — check temp/logs/api.err.log and bot.err.log"
exit 2
