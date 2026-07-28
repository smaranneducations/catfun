#!/usr/bin/env bash
# Helper: run silent start in an interactive Terminal session
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
unset npm_config_devdir || true
echo "Stopping any old services..."
./stop-silent.sh || true
sleep 1
echo "Starting AI Brief silently..."
./start-silent.sh
echo
echo "--- status ---"
./status-silent.sh || true
echo
echo "Done. You can close this Terminal window; services keep running in the background."
