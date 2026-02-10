"""Upload Tracker for FinanceCats.

Maintains a complete audit log of every YouTube upload attempt — successes,
failures, retries, and metadata. Useful for the orchestrator (to know what's
published) and the admin (to debug issues, track performance, retry failures).

Data stored in upload_log.json alongside episode_log.json.
"""
import os
import json
import time
from datetime import datetime, timezone
import config

UPLOAD_LOG_PATH = os.path.join(config.BASE_DIR, "upload_log.json")


def _load_log() -> dict:
    """Load the upload log."""
    if os.path.exists(UPLOAD_LOG_PATH):
        with open(UPLOAD_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "channel": "FinanceCats",
        "total_uploads": 0,
        "total_failures": 0,
        "uploads": [],
    }


def _save_log(log: dict):
    """Save the upload log."""
    with open(UPLOAD_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def log_upload(
    term: str,
    title: str,
    video_path: str,
    thumbnail_path: str = "",
    youtube_video_id: str = "",
    youtube_url: str = "",
    playlist_id: str = "",
    playlist_name: str = "",
    privacy: str = "public",
    category_id: str = "27",
    tags: list[str] = None,
    description: str = "",
    status: str = "success",
    error_message: str = "",
    episode_number: int = 0,
    series_id: int = 0,
    series_position: int = 0,
    news_source: str = "",
    news_clip_date: str = "",
    duration_seconds: float = 0,
    file_size_mb: float = 0,
) -> dict:
    """Log a YouTube upload attempt (success or failure).

    Returns the log entry that was created.
    """
    log = _load_log()

    now = datetime.now(timezone.utc)
    entry = {
        "id": len(log["uploads"]) + 1,
        "timestamp_utc": now.isoformat(),
        "timestamp_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,  # "success", "failed", "skipped"

        # Content info
        "term": term,
        "title": title,
        "episode_number": episode_number,
        "series_id": series_id,
        "series_position": series_position,

        # YouTube info
        "youtube_video_id": youtube_video_id,
        "youtube_url": youtube_url,
        "playlist_id": playlist_id,
        "playlist_name": playlist_name,
        "privacy": privacy,
        "category_id": category_id,
        "tags": tags or [],
        "description_preview": description[:200] if description else "",

        # File info
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "duration_seconds": duration_seconds,
        "file_size_mb": round(file_size_mb, 2),

        # Source info
        "news_source": news_source,
        "news_clip_date": news_clip_date,

        # Error info (if failed)
        "error_message": error_message,
    }

    log["uploads"].append(entry)

    if status == "success":
        log["total_uploads"] += 1
    elif status == "failed":
        log["total_failures"] += 1

    _save_log(log)

    status_icon = "OK" if status == "success" else "FAIL" if status == "failed" else "SKIP"
    print(f"    [Upload Tracker] [{status_icon}] #{entry['id']} — {title}")
    if youtube_url:
        print(f"    [Upload Tracker] URL: {youtube_url}")

    return entry


def get_upload_history(limit: int = 20) -> list[dict]:
    """Get the most recent upload entries."""
    log = _load_log()
    return log["uploads"][-limit:]


def get_failed_uploads() -> list[dict]:
    """Get all failed uploads (for retry)."""
    log = _load_log()
    return [u for u in log["uploads"] if u["status"] == "failed"]


def get_successful_uploads() -> list[dict]:
    """Get all successful uploads."""
    log = _load_log()
    return [u for u in log["uploads"] if u["status"] == "success"]


def get_upload_stats() -> dict:
    """Get summary statistics."""
    log = _load_log()
    uploads = log["uploads"]
    successful = [u for u in uploads if u["status"] == "success"]
    failed = [u for u in uploads if u["status"] == "failed"]

    return {
        "total_attempts": len(uploads),
        "successful": len(successful),
        "failed": len(failed),
        "skipped": len([u for u in uploads if u["status"] == "skipped"]),
        "total_duration_minutes": round(
            sum(u.get("duration_seconds", 0) for u in successful) / 60, 1
        ),
        "total_size_mb": round(
            sum(u.get("file_size_mb", 0) for u in successful), 1
        ),
        "youtube_urls": [u["youtube_url"] for u in successful if u.get("youtube_url")],
        "terms_published": [u["term"] for u in successful],
        "last_upload": successful[-1]["timestamp_local"] if successful else "Never",
    }


def print_dashboard():
    """Print a quick dashboard of upload status."""
    stats = get_upload_stats()
    print("\n" + "=" * 50)
    print("  UPLOAD DASHBOARD")
    print("=" * 50)
    print(f"  Total uploads: {stats['successful']} successful, {stats['failed']} failed")
    print(f"  Total content: {stats['total_duration_minutes']} min, {stats['total_size_mb']} MB")
    print(f"  Last upload: {stats['last_upload']}")
    if stats['youtube_urls']:
        print(f"  Latest video: {stats['youtube_urls'][-1]}")
    print(f"  Terms published: {', '.join(stats['terms_published']) or 'None yet'}")
    print("=" * 50 + "\n")
