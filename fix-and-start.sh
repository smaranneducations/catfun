#!/usr/bin/env bash
# Fix Mac setup + restart AI Brief Discord bot cleanly.
# Run this in Terminal.app (not inside Cursor).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
unset npm_config_devdir || true

echo "==> Stopping old processes..."
./stop-silent.sh || true
pkill -9 -f "$ROOT/discord-bot" 2>/dev/null || true
pkill -9 -f "aibrief\.api" 2>/dev/null || true
for port in 8900 8901; do
  for pid in $(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true); do
    echo "    kill port $port pid $pid"
    kill -9 "$pid" 2>/dev/null || true
  done
done
sleep 1

echo "==> Ensuring better-sqlite3 is built for macOS..."
cd "$ROOT/discord-bot"
if ! node -e "require('better-sqlite3'); new (require('better-sqlite3'))(':memory:').close()" 2>/dev/null; then
  echo "    rebuilding native module (was Windows binary from OneDrive)..."
  rm -rf node_modules/better-sqlite3/build
  npm rebuild better-sqlite3
else
  echo "    native module OK"
fi

echo "==> Recovering SQLite (OneDrive / leftover Windows WAL)..."
rm -f data/bot.pid
node <<'NODE'
const Database = require("better-sqlite3");
const fs = require("fs");
const db = new Database("data/aibrief.db", { timeout: 10000 });
try {
  db.pragma("busy_timeout = 10000");
  db.pragma("wal_checkpoint(TRUNCATE)");
} catch (e) {
  console.warn("    checkpoint warning:", e.message);
}
try {
  db.pragma("journal_mode = DELETE");
} catch (e) {
  console.warn("    journal_mode warning:", e.message);
}
db.close();
for (const f of ["data/aibrief.db-shm", "data/aibrief.db-wal"]) {
  try { fs.unlinkSync(f); } catch {}
}
console.log("    database ready");
NODE

cd "$ROOT"
echo "==> Starting services..."
./start-silent.sh
echo
./status-silent.sh
echo
echo "If status looks good, try /ping again in Discord."
