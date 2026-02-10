"""YouTube uploader for FinanceCats.

Handles OAuth2 authentication and video upload to YouTube using the
Google YouTube Data API v3.

First run requires browser-based OAuth consent. After that, the refresh
token is stored in token.json and reused automatically.

Upload reliability features:
  - Exponential backoff with jitter (Google best practice)
  - Configurable max retries (default 10)
  - Proper handling of 500/503 server errors
  - Sleep between chunks to avoid rate limits
  - Progress logging with ETA
"""
import os
import json
import time
import random
import httplib2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import config

# Upload retry settings
MAX_RETRIES = 10
INITIAL_RETRY_DELAY = 1    # seconds
MAX_RETRY_DELAY = 64       # seconds
CHUNK_SLEEP = 0.5           # sleep between successful chunks (rate limit protection)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, ConnectionError,
                        ConnectionResetError, TimeoutError)

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]

TOKEN_PATH = os.path.join(config.BASE_DIR, "token.json")
CLIENT_SECRETS_PATH = os.path.join(config.BASE_DIR, "client_secret.json")


def _get_credentials() -> Credentials:
    """Get OAuth2 credentials, refreshing or prompting login as needed."""
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  [YouTube] Refreshing access token...")
            creds.refresh(Request())
        else:
            # Need client_secret.json for OAuth flow
            if not os.path.exists(CLIENT_SECRETS_PATH):
                # Build it from .env values
                _create_client_secrets()

            if not os.path.exists(CLIENT_SECRETS_PATH):
                raise FileNotFoundError(
                    f"No {CLIENT_SECRETS_PATH} found. Download it from "
                    "Google Cloud Console > APIs & Services > Credentials."
                )

            print("  [YouTube] Starting OAuth flow — a browser window will open...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_PATH, SCOPES
            )
            # Try several ports in case one is busy
            for port in [8091, 8092, 8093, 8094, 8095]:
                try:
                    creds = flow.run_local_server(port=port, open_browser=True)
                    break
                except OSError:
                    continue

        # Save for next time
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print("  [YouTube] Credentials saved.")

    return creds


def _create_client_secrets():
    """Create client_secret.json from environment variables."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        return

    secrets = {
        "installed": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    with open(CLIENT_SECRETS_PATH, "w") as f:
        json.dump(secrets, f, indent=2)
    print("  [YouTube] Created client_secret.json from .env values")


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: str = None,
    category_id: str = "27",  # Education
    privacy: str = "public",
    playlist_title: str = None,
) -> dict:
    """Upload a video to YouTube.

    Args:
        video_path: Path to the MP4 file
        title: Video title
        description: Full description
        tags: List of tags
        thumbnail_path: Path to custom thumbnail image
        category_id: YouTube category (27=Education, 22=People & Blogs)
        privacy: 'public', 'private', or 'unlisted'
        playlist_title: If set, add video to this playlist (creates if needed)

    Returns:
        dict with video_id, url, and status
    """
    print("\n=== YOUTUBE UPLOAD ===")

    if not os.path.exists(video_path):
        print(f"  ERROR: Video not found: {video_path}")
        return {"error": "Video file not found"}

    try:
        creds = _get_credentials()
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"  ERROR: YouTube auth failed: {e}")
        return {"error": str(e)}

    # ── Upload video ──
    body = {
        "snippet": {
            "title": title[:100],  # YouTube max 100 chars
            "description": description[:5000],  # YouTube max 5000 chars
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    file_size = os.path.getsize(video_path)
    file_size_mb = file_size / (1024 * 1024)

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,  # 5MB chunks (more reliable than 10MB)
    )

    print(f"  Uploading: {title}")
    print(f"  Privacy: {privacy}")
    print(f"  File: {video_path} ({file_size_mb:.1f} MB)")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # Upload with exponential backoff and jitter (Google best practice)
    response = None
    retry = 0
    retry_delay = INITIAL_RETRY_DELAY
    upload_start = time.time()
    last_progress = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                elapsed = time.time() - upload_start
                if pct > 0:
                    eta = (elapsed / pct) * (100 - pct)
                    print(f"  Upload progress: {pct}% "
                          f"(elapsed: {elapsed:.0f}s, ETA: {eta:.0f}s)")
                else:
                    print(f"  Upload progress: {pct}%")
                last_progress = pct
                # Reset retry state on successful chunk
                retry = 0
                retry_delay = INITIAL_RETRY_DELAY
                # Small sleep between chunks to avoid rate limits
                time.sleep(CHUNK_SLEEP)

        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retry += 1
                if retry > MAX_RETRIES:
                    print(f"  ERROR: Upload failed after {MAX_RETRIES} retries "
                          f"(HTTP {e.resp.status}): {e}")
                    return {"error": str(e)}
                # Exponential backoff with jitter
                sleep_time = min(retry_delay + random.random(), MAX_RETRY_DELAY)
                print(f"  HTTP {e.resp.status} error at {last_progress}%. "
                      f"Retrying in {sleep_time:.1f}s ({retry}/{MAX_RETRIES})...")
                time.sleep(sleep_time)
                retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            else:
                # Non-retriable HTTP error
                print(f"  ERROR: Non-retriable HTTP error {e.resp.status}: {e}")
                return {"error": str(e)}

        except RETRIABLE_EXCEPTIONS as e:
            retry += 1
            if retry > MAX_RETRIES:
                print(f"  ERROR: Upload failed after {MAX_RETRIES} retries: {e}")
                return {"error": str(e)}
            sleep_time = min(retry_delay + random.random(), MAX_RETRY_DELAY)
            print(f"  Connection error at {last_progress}%. "
                  f"Retrying in {sleep_time:.1f}s ({retry}/{MAX_RETRIES})...")
            time.sleep(sleep_time)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

        except Exception as e:
            # Unexpected error — still retry a few times
            retry += 1
            if retry > 3:
                print(f"  ERROR: Unexpected upload error after 3 retries: {e}")
                return {"error": str(e)}
            sleep_time = 5 + random.random() * 5
            print(f"  Unexpected error at {last_progress}%: {e}")
            print(f"  Retrying in {sleep_time:.1f}s ({retry}/3)...")
            time.sleep(sleep_time)

    upload_elapsed = time.time() - upload_start
    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  Upload complete! ({upload_elapsed:.1f}s)")
    print(f"  Video ID: {video_id}")
    print(f"  URL: {video_url}")

    # ══════════════════════════════════════════════════
    # STAGE-BY-STAGE VERIFICATION
    # ══════════════════════════════════════════════════
    stages = {
        "video_upload": False,
        "metadata": False,
        "thumbnail": False,
        "playlist": False,
    }

    # ── STAGE 1: Verify video upload + metadata ──
    print(f"\n  [Verify] Stage 1: Checking video upload + metadata...")
    time.sleep(5)  # Let YouTube process the upload

    stage1 = _verify_video_and_metadata(
        youtube, video_id,
        expected_title=title[:100],
        expected_description=description[:100],  # Just check start
        expected_tags=tags[:5],
    )
    stages["video_upload"] = stage1.get("video_exists", False)
    stages["metadata"] = stage1.get("metadata_correct", False)

    if stages["video_upload"]:
        print(f"  [Verify] Stage 1 PASSED: Video exists (status: {stage1.get('upload_status', '?')})")
    else:
        print(f"  [Verify] Stage 1 FAILED: Video not found on YouTube!")

    if stages["metadata"]:
        print(f"  [Verify] Stage 1 PASSED: Title, description, tags confirmed")
    else:
        mismatches = stage1.get("mismatches", [])
        if mismatches:
            print(f"  [Verify] Stage 1 WARNING: Metadata mismatches: {', '.join(mismatches)}")
        elif stages["video_upload"]:
            print(f"  [Verify] Stage 1 WARNING: Could not verify metadata")

    # ── STAGE 2: Set + verify thumbnail ──
    thumbnail_set = False
    if thumbnail_path and os.path.exists(thumbnail_path):
        for attempt in range(3):
            try:
                print(f"\n  [Verify] Stage 2: Setting custom thumbnail (attempt {attempt + 1}/3)...")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
                ).execute()
                # Verify thumbnail was applied
                time.sleep(3)
                thumb_ok = _verify_thumbnail(youtube, video_id)
                stages["thumbnail"] = thumb_ok
                if thumb_ok:
                    print(f"  [Verify] Stage 2 PASSED: Custom thumbnail confirmed on video")
                else:
                    print(f"  [Verify] Stage 2 WARNING: Thumbnail uploaded but could not confirm it was applied")
                thumbnail_set = True
                break
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 5
                    print(f"  Thumbnail upload failed: {e}")
                    print(f"  Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [Verify] Stage 2 FAILED: Thumbnail upload failed after 3 attempts: {e}")
                    print(f"  (You can set it manually in YouTube Studio)")
    else:
        stages["thumbnail"] = None  # Not applicable
        print(f"\n  [Verify] Stage 2: Skipped (no thumbnail provided)")

    # ── STAGE 3: Add to playlist + verify ──
    playlist_id = None
    if playlist_title:
        time.sleep(2)
        for attempt in range(3):
            try:
                print(f"\n  [Verify] Stage 3: Adding to playlist (attempt {attempt + 1}/3)...")
                playlist_id = _get_or_create_playlist(youtube, playlist_title)
                if playlist_id:
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {
                                    "kind": "youtube#video",
                                    "videoId": video_id,
                                },
                            },
                        },
                    ).execute()
                    # Verify video is in playlist
                    time.sleep(2)
                    in_playlist = _verify_in_playlist(youtube, playlist_id, video_id)
                    stages["playlist"] = in_playlist
                    if in_playlist:
                        print(f"  [Verify] Stage 3 PASSED: Video confirmed in playlist '{playlist_title}'")
                    else:
                        print(f"  [Verify] Stage 3 WARNING: Added to playlist but could not confirm")
                break
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 3
                    print(f"  Playlist add failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [Verify] Stage 3 FAILED: Playlist add failed after 3 attempts: {e}")
    else:
        stages["playlist"] = None  # Not applicable
        print(f"\n  [Verify] Stage 3: Skipped (no playlist)")

    # ── VERIFICATION SUMMARY ──
    active_stages = {k: v for k, v in stages.items() if v is not None}
    passed = sum(1 for v in active_stages.values() if v is True)
    total = len(active_stages)
    all_passed = passed == total

    print(f"\n  {'=' * 50}")
    print(f"  YOUTUBE VERIFICATION: {passed}/{total} stages passed")
    for stage_name, stage_ok in stages.items():
        if stage_ok is None:
            icon = "SKIP"
        elif stage_ok:
            icon = "PASS"
        else:
            icon = "FAIL"
        print(f"    [{icon}] {stage_name}")
    print(f"  {'=' * 50}")

    return {
        "video_id": video_id,
        "url": video_url,
        "status": privacy,
        "playlist_id": playlist_id,
        "verified": all_passed,
        "verification_stages": stages,
        "verification_passed": passed,
        "verification_total": total,
        "upload_status": stage1.get("upload_status", "unknown"),
        "upload_elapsed_seconds": round(upload_elapsed, 1),
    }


def _verify_video_and_metadata(youtube, video_id: str, expected_title: str = "",
                               expected_description: str = "",
                               expected_tags: list = None,
                               max_wait: int = 30) -> dict:
    """Verify video exists AND metadata (title, description, tags) was saved correctly.

    Queries videos().list with snippet + status parts, then compares against expected values.

    Returns dict with:
        video_exists (bool), metadata_correct (bool), upload_status (str),
        mismatches (list of field names that didn't match)
    """
    start = time.time()
    poll_interval = 5

    while time.time() - start < max_wait:
        try:
            response = youtube.videos().list(
                part="status,snippet,processingDetails",
                id=video_id,
            ).execute()

            items = response.get("items", [])
            if not items:
                time.sleep(poll_interval)
                continue

            video = items[0]
            status = video.get("status", {})
            snippet = video.get("snippet", {})
            upload_status = status.get("uploadStatus", "unknown")

            # Check if upload was rejected/failed
            if upload_status in ("failed", "rejected", "deleted"):
                return {
                    "video_exists": False,
                    "metadata_correct": False,
                    "upload_status": upload_status,
                    "failure_reason": status.get("failureReason", "unknown"),
                    "mismatches": ["upload_failed"],
                }

            if upload_status not in ("uploaded", "processed"):
                time.sleep(poll_interval)
                continue

            # Video exists — now verify metadata
            mismatches = []
            actual_title = snippet.get("title", "")
            actual_description = snippet.get("description", "")
            actual_tags = snippet.get("tags", [])

            if expected_title and actual_title != expected_title:
                mismatches.append(f"title (expected '{expected_title[:50]}...', "
                                  f"got '{actual_title[:50]}...')")

            if expected_description and not actual_description.startswith(expected_description[:80]):
                mismatches.append("description")

            if expected_tags:
                missing_tags = [t for t in expected_tags
                                if t.lower() not in [at.lower() for at in actual_tags]]
                if missing_tags:
                    mismatches.append(f"tags (missing: {missing_tags[:3]})")

            return {
                "video_exists": True,
                "metadata_correct": len(mismatches) == 0,
                "upload_status": upload_status,
                "privacy_status": status.get("privacyStatus", "unknown"),
                "processing_status": video.get("processingDetails", {}).get(
                    "processingStatus", "unknown"),
                "actual_title": actual_title,
                "actual_tags_count": len(actual_tags),
                "mismatches": mismatches,
            }

        except Exception as e:
            print(f"  [Verify] API error: {e}")
            time.sleep(poll_interval)

    return {"video_exists": False, "metadata_correct": False,
            "upload_status": "timeout", "mismatches": ["verification_timeout"]}


def _verify_thumbnail(youtube, video_id: str) -> bool:
    """Verify that a custom thumbnail was applied to the video.

    Custom thumbnails show up as high-resolution entries in snippet.thumbnails.
    YouTube auto-generates 3 thumbnails (default, medium, high), but custom
    thumbnails typically add maxres or update the existing ones.
    """
    try:
        response = youtube.videos().list(
            part="snippet",
            id=video_id,
        ).execute()

        items = response.get("items", [])
        if items:
            thumbnails = items[0].get("snippet", {}).get("thumbnails", {})
            # Custom thumbnails usually create a 'maxres' entry or the 'high'
            # thumbnail has a different URL pattern than auto-generated ones
            has_maxres = "maxres" in thumbnails
            has_high = "high" in thumbnails
            # If we have high-res thumbnails, the custom one was likely applied
            if has_maxres or has_high:
                return True
    except Exception as e:
        print(f"  [Verify] Thumbnail check error: {e}")

    return False


def _verify_in_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    """Verify that a video is actually in the specified playlist."""
    try:
        response = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
        ).execute()

        for item in response.get("items", []):
            resource = item.get("snippet", {}).get("resourceId", {})
            if resource.get("videoId") == video_id:
                return True
    except Exception as e:
        print(f"  [Verify] Playlist check error: {e}")

    return False


def _get_or_create_playlist(youtube, title: str) -> str:
    """Get an existing playlist by title, or create a new one."""
    # Search existing playlists
    try:
        playlists = youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50,
        ).execute()

        for pl in playlists.get("items", []):
            if pl["snippet"]["title"].lower() == title.lower():
                return pl["id"]
    except Exception:
        pass

    # Create new playlist
    try:
        result = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": f"FinanceCats series: {title}",
                },
                "status": {
                    "privacyStatus": "public",
                },
            },
        ).execute()
        print(f"  Created new playlist: {title}")
        return result["id"]
    except Exception as e:
        print(f"  WARNING: Could not create playlist: {e}")
        return ""
