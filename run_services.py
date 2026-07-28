#!/usr/bin/env python3
"""
Simple service launcher for AI Brief on Windows.

Usage (PowerShell):
  python "C:\\Users\\conta\\OneDrive\\Projects\\catfun\\run_services.py" start
  python "C:\\Users\\conta\\OneDrive\\Projects\\catfun\\run_services.py" status
  python "C:\\Users\\conta\\OneDrive\\Projects\\catfun\\run_services.py" stop

What it does:
  - start: kills old listeners on 8900/8901, starts API + bot in background,
           prints health + quick log tail, then exits
  - status: prints current status + log tail
  - stop: stops tracked PIDs and listeners on 8900/8901
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DISCORD_DIR = ROOT / "discord-bot"
LOG_DIR = ROOT / "temp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

API_OUT = LOG_DIR / "api.out.log"
API_ERR = LOG_DIR / "api.err.log"
BOT_OUT = LOG_DIR / "bot.out.log"
BOT_ERR = LOG_DIR / "bot.err.log"
PID_FILE = LOG_DIR / "services.pids.json"

API_PORT = 8900
BOT_LOCK_PORT = 8901


def _is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _http_ok() -> bool:
    # avoid extra deps; use urllib from stdlib
    import urllib.request

    try:
        with urllib.request.urlopen("http://127.0.0.1:8900/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    # hard kill via taskkill on Windows
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        shell=False,
    )


def _pids_listening_on_port(port: int) -> list[int]:
    # netstat is stable on Windows
    result = subprocess.run(
        ["cmd", "/c", "netstat -ano | findstr LISTENING"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        if f":{port}" not in line:
            continue
        parts = line.split()
        if len(parts) >= 5:
            try:
                pids.append(int(parts[-1]))
            except ValueError:
                pass
    return sorted(set(pids))


def _kill_ports() -> None:
    for port in (API_PORT, BOT_LOCK_PORT):
        pids = _pids_listening_on_port(port)
        if pids:
            print(f"[cleanup] Port {port} -> killing PIDs: {pids}")
            for pid in pids:
                _kill_pid(pid)
        else:
            print(f"[cleanup] Port {port} is free")


def _tail(path: Path, lines: int = 12) -> str:
    if not path.exists():
        return "(no log file)"
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not text:
        return "(empty)"
    return "\n".join(text[-lines:])


def _start_background() -> dict[str, int]:
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )

    api_out_f = API_OUT.open("w", encoding="utf-8", errors="replace")
    api_err_f = API_ERR.open("w", encoding="utf-8", errors="replace")
    bot_out_f = BOT_OUT.open("w", encoding="utf-8", errors="replace")
    bot_err_f = BOT_ERR.open("w", encoding="utf-8", errors="replace")

    api_proc = subprocess.Popen(
        [sys.executable, "-m", "aibrief.api", "--port", str(API_PORT)],
        cwd=str(ROOT),
        stdout=api_out_f,
        stderr=api_err_f,
        creationflags=creationflags,
        shell=False,
    )

    # npm on Windows is safest via cmd /c
    bot_proc = subprocess.Popen(
        ["cmd", "/c", "npm run dev"],
        cwd=str(DISCORD_DIR),
        stdout=bot_out_f,
        stderr=bot_err_f,
        creationflags=creationflags,
        shell=False,
    )

    # close parent file handles
    api_out_f.close()
    api_err_f.close()
    bot_out_f.close()
    bot_err_f.close()

    return {"api_pid": api_proc.pid, "bot_pid": bot_proc.pid}


def _save_pids(pids: dict[str, int]) -> None:
    PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")


def _load_pids() -> dict[str, int]:
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def cmd_start() -> int:
    if not (ROOT / "aibrief" / "api.py").exists():
        print("[error] aibrief/api.py not found")
        return 1
    if not (DISCORD_DIR / "package.json").exists():
        print("[error] discord-bot/package.json not found")
        return 1

    print("[start] Cleaning old listeners...")
    _kill_ports()
    time.sleep(1)

    pids: dict[str, int] = {}

    # Reuse healthy existing services when they already run.
    api_already_ok = _http_ok()
    bot_already_ok = _is_port_listening(BOT_LOCK_PORT)

    if api_already_ok:
        print("[start] API already healthy on 8900 -> reusing existing process")
    if bot_already_ok:
        print("[start] Bot lock already listening on 8901 -> reusing existing process")

    if not (api_already_ok and bot_already_ok):
        print("[start] Launching missing services in background...")
        started = _start_background()
        pids.update(started)
        _save_pids(pids)
        if "api_pid" in started:
            print(f"[start] API PID: {started['api_pid']}")
        if "bot_pid" in started:
            print(f"[start] BOT PID: {started['bot_pid']}")
    else:
        # Keep old PID file if present.
        if not PID_FILE.exists():
            _save_pids({})

    api_ok = False
    bot_ok = False
    for _ in range(60):
        time.sleep(1)
        api_ok = _http_ok()
        bot_ok = _is_port_listening(BOT_LOCK_PORT)
        if api_ok and bot_ok:
            break

    print("\n[status]")
    print(f"  API health (8900): {'OK' if api_ok else 'NOT READY'}")
    print(f"  Bot lock port (8901): {'LISTENING' if bot_ok else 'NOT READY'}")

    print("\n[api.err.log tail]")
    print(_tail(API_ERR))
    print("\n[bot.err.log tail]")
    print(_tail(BOT_ERR))

    print("\nDone. You can close this PowerShell window.")
    print(f"Logs: {LOG_DIR}")
    return 0 if (api_ok and bot_ok) else 2


def cmd_status() -> int:
    pids = _load_pids()
    print("[status]")
    print(f"  Stored PIDs: {pids if pids else '(none)'}")
    print(f"  API health (8900): {'OK' if _http_ok() else 'DOWN'}")
    print(
        f"  Bot lock port (8901): {'LISTENING' if _is_port_listening(BOT_LOCK_PORT) else 'DOWN'}"
    )
    print("\n[api.err.log tail]")
    print(_tail(API_ERR))
    print("\n[bot.err.log tail]")
    print(_tail(BOT_ERR))
    return 0


def cmd_stop() -> int:
    print("[stop] Stopping tracked processes...")
    pids = _load_pids()
    for key in ("api_pid", "bot_pid"):
        pid = pids.get(key)
        if isinstance(pid, int):
            print(f"  - killing {key}: {pid}")
            _kill_pid(pid)

    print("[stop] Cleaning listener ports...")
    _kill_ports()
    print("[stop] Done.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Brief service launcher")
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "status", "stop"],
        help="start|status|stop",
    )
    args = parser.parse_args()

    if args.command == "start":
        return cmd_start()
    if args.command == "status":
        return cmd_status()
    return cmd_stop()


if __name__ == "__main__":
    raise SystemExit(main())

