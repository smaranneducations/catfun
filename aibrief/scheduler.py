"""Silent Scheduler — Runs AI Brief randomly 3 times per 24 hours.

How it works:
  1. Divides 24 hours into 3 segments (~8 hours each)
  2. Picks a random time within each segment
  3. Sleeps until that time, runs the pipeline, repeats
  4. Loops forever

Runs silently via pythonw.exe (no console window).
All output goes to aibrief/scheduler.log.

Setup:
    python -m aibrief.scheduler --install    # Register in Task Scheduler
    python -m aibrief.scheduler --uninstall  # Remove from Task Scheduler
    python -m aibrief.scheduler --run        # Run once for testing
    python -m aibrief.scheduler              # Start the loop (used by Task Scheduler)
"""
import sys
import os
import random
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Fix encoding for logging
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
LOG_FILE = BASE_DIR / "scheduler.log"
STATE_FILE = BASE_DIR / "scheduler_state.json"

# ── Config ──
RUNS_PER_DAY = 3
MIN_GAP_HOURS = 2.0      # Minimum gap between runs
QUIET_START = 23          # Don't start runs after 11 PM
QUIET_END = 7             # Don't start runs before 7 AM
MAX_RETRIES = 2           # Retry on failure

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("scheduler")


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"runs_today": 0, "last_run": None, "total_runs": 0,
            "last_date": None}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str),
                          encoding="utf-8")


def _generate_run_times() -> list[float]:
    """Generate 3 random run times (as hours from now) spread across 24h.

    Divides 24h into segments, picks random time in each.
    Respects quiet hours (no runs between 11 PM and 7 AM).
    """
    now = datetime.now()
    segment = 24.0 / RUNS_PER_DAY
    times = []

    for i in range(RUNS_PER_DAY):
        start_h = i * segment + 0.5
        end_h = (i + 1) * segment - 0.5

        # Try up to 10 times to find a non-quiet-hour slot
        for _ in range(10):
            h = random.uniform(start_h, end_h)
            target = now + timedelta(hours=h)
            hour = target.hour
            if not (QUIET_START <= hour or hour < QUIET_END):
                times.append(h)
                break
        else:
            # All attempts fell in quiet hours — shift to just after quiet
            times.append(max(start_h, QUIET_END - now.hour + 0.5))

    return sorted(times)


def _run_pipeline() -> bool:
    """Run the AI Brief pipeline. Returns True on success."""
    log.info("=" * 50)
    log.info("STARTING AI BRIEF PIPELINE")
    log.info("=" * 50)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "aibrief.main"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,   # 15 minute timeout
        )

        # Log output
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-30:]:
                log.info(f"  {line}")

        if result.returncode == 0:
            log.info("PIPELINE SUCCESS")
            return True
        else:
            log.error(f"PIPELINE FAILED (exit code {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-10:]:
                    log.error(f"  {line}")
            return False

    except subprocess.TimeoutExpired:
        log.error("PIPELINE TIMEOUT (>15 min)")
        return False
    except Exception as e:
        log.error(f"PIPELINE ERROR: {e}")
        return False


def run_loop():
    """Main loop — runs forever, 3 times per 24 hours at random times."""
    log.info("=" * 60)
    log.info("AI BRIEF SCHEDULER STARTED")
    log.info(f"  Runs per day: {RUNS_PER_DAY}")
    log.info(f"  Quiet hours: {QUIET_START}:00 - {QUIET_END}:00")
    log.info(f"  Log: {LOG_FILE}")
    log.info("=" * 60)

    while True:
        state = _load_state()
        today = datetime.now().strftime("%Y-%m-%d")

        # Reset counter if new day
        if state.get("last_date") != today:
            state["runs_today"] = 0
            state["last_date"] = today
            _save_state(state)

        # Generate today's run schedule
        run_times = _generate_run_times()
        log.info(f"Today's schedule: runs in {[f'{h:.1f}h' for h in run_times]}")

        completed = 0
        clock_start = time.time()

        for i, hours_from_now in enumerate(run_times):
            # Calculate sleep time
            elapsed = (time.time() - clock_start) / 3600
            sleep_hours = max(0, hours_from_now - elapsed)
            sleep_seconds = int(sleep_hours * 3600)

            if sleep_seconds > 0:
                wake_time = datetime.now() + timedelta(seconds=sleep_seconds)
                log.info(f"Run {i+1}/{RUNS_PER_DAY}: sleeping {sleep_hours:.1f}h "
                         f"(wake at {wake_time.strftime('%H:%M')})")

                # Sleep in chunks (so we can be interrupted gracefully)
                remaining = sleep_seconds
                while remaining > 0:
                    chunk = min(remaining, 300)  # 5-minute chunks
                    time.sleep(chunk)
                    remaining -= chunk

            # Run the pipeline
            log.info(f"Run {i+1}/{RUNS_PER_DAY}: EXECUTING at "
                     f"{datetime.now().strftime('%H:%M:%S')}")

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                success = _run_pipeline()
                if success:
                    break
                if attempt < MAX_RETRIES:
                    log.warning(f"Retry {attempt}/{MAX_RETRIES} in 60s...")
                    time.sleep(60)

            # Update state
            state = _load_state()
            state["runs_today"] = state.get("runs_today", 0) + 1
            state["last_run"] = datetime.now().isoformat()
            state["total_runs"] = state.get("total_runs", 0) + 1
            state["last_success"] = success
            _save_state(state)

            completed += 1
            log.info(f"Run {i+1} done. Today: {state['runs_today']}/{RUNS_PER_DAY}. "
                     f"Total: {state['total_runs']}.")

        # Sleep until next day cycle
        elapsed_total = (time.time() - clock_start) / 3600
        remaining_hours = max(0.5, 24 - elapsed_total)
        log.info(f"All {RUNS_PER_DAY} runs complete. "
                 f"Sleeping {remaining_hours:.1f}h until next cycle.")
        time.sleep(int(remaining_hours * 3600))


def run_once():
    """Run the pipeline once (for testing)."""
    log.info("MANUAL RUN (--run)")
    success = _run_pipeline()
    log.info(f"Result: {'SUCCESS' if success else 'FAILED'}")
    return success


def install_task():
    """Register in Windows Task Scheduler to run at login, silently."""
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = sys.executable  # fallback

    task_name = "AIBrief_AutoPublisher"
    command = (
        f'schtasks /create /tn "{task_name}" '
        f'/tr "\\"{pythonw}\\" -m aibrief.scheduler" '
        f'/sc onlogon '
        f'/rl highest '
        f'/f '
        f'/sd {datetime.now().strftime("%m/%d/%Y")}'
    )

    print(f"  Installing Task Scheduler task: {task_name}")
    print(f"  Python: {pythonw}")
    print(f"  Working dir: {PROJECT_DIR}")
    print()

    # Create a wrapper bat file (Task Scheduler works better with bat)
    bat_path = BASE_DIR / "run_scheduler.bat"
    bat_path.write_text(
        f'@echo off\n'
        f'cd /d "{PROJECT_DIR}"\n'
        f'"{pythonw}" -m aibrief.scheduler\n',
        encoding="utf-8"
    )

    cmd = (
        f'schtasks /create /tn "{task_name}" '
        f'/tr "\\"{bat_path}\\"" '
        f'/sc onlogon '
        f'/rl highest '
        f'/f'
    )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Task '{task_name}' installed successfully!")
        print(f"  It will start automatically on next login.")
        print(f"  To start now: schtasks /run /tn \"{task_name}\"")
        print(f"  To check: schtasks /query /tn \"{task_name}\"")
        print(f"  Log: {LOG_FILE}")
    else:
        print(f"  ERROR: {result.stderr}")
        print(f"  Try running as Administrator.")


def uninstall_task():
    """Remove from Task Scheduler."""
    task_name = "AIBrief_AutoPublisher"
    result = subprocess.run(
        f'schtasks /delete /tn "{task_name}" /f',
        shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Task '{task_name}' removed.")
    else:
        print(f"  {result.stderr.strip() or 'Task not found.'}")


if __name__ == "__main__":
    if "--install" in sys.argv:
        install_task()
    elif "--uninstall" in sys.argv:
        uninstall_task()
    elif "--run" in sys.argv:
        run_once()
    else:
        run_loop()
