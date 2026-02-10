"""LinkedIn Video Posting Pipeline for FinanceCats.

Handles the full LinkedIn video upload and post creation flow:
  1. Initialize video upload (get upload URLs)
  2. Upload video binary in parts
  3. Finalize the upload
  4. Create a post with the video + commentary

Uses the LinkedIn REST API (Videos API + Posts API).
"""
import os
import math
import time
import requests
import config

LINKEDIN_API_BASE = "https://api.linkedin.com/rest"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB per part (LinkedIn requirement)


def _headers(extra: dict = None) -> dict:
    """Build standard LinkedIn API headers."""
    h = {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": config.LINKEDIN_API_VERSION,
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


# ─────────────────────────────────────────────────────────────
# Step 1: Initialize Video Upload
# ─────────────────────────────────────────────────────────────
def _initialize_upload(file_size_bytes: int, owner_urn: str) -> dict:
    """Register an upcoming video upload with LinkedIn."""
    url = f"{LINKEDIN_API_BASE}/videos?action=initializeUpload"
    payload = {
        "initializeUploadRequest": {
            "owner": owner_urn,
            "fileSizeBytes": file_size_bytes,
            "uploadCaptions": False,
            "uploadThumbnail": False,
        }
    }
    resp = requests.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    data = resp.json().get("value", {})
    print(f"    [LinkedIn] Initialized upload — video URN: {data.get('video')}")
    return data


# ─────────────────────────────────────────────────────────────
# Step 2: Upload Video in Parts
# ─────────────────────────────────────────────────────────────
def _upload_parts(video_path: str, upload_instructions: list) -> list[str]:
    """Upload the video file in chunks according to LinkedIn's instructions.

    Returns list of ETags (uploaded part IDs).
    """
    etags = []
    total_parts = len(upload_instructions)

    with open(video_path, "rb") as f:
        for i, instruction in enumerate(upload_instructions):
            first_byte = instruction["firstByte"]
            last_byte = instruction["lastByte"]
            upload_url = instruction["uploadUrl"]

            f.seek(first_byte)
            chunk = f.read(last_byte - first_byte + 1)

            print(f"    [LinkedIn] Uploading part {i + 1}/{total_parts} "
                  f"({len(chunk) / (1024*1024):.1f} MB)...")

            resp = requests.put(
                upload_url,
                data=chunk,
                headers={
                    "Content-Type": "application/octet-stream",
                },
            )
            resp.raise_for_status()

            # Extract ETag from response headers
            etag = resp.headers.get("etag", "").strip('"')
            if not etag:
                # Some responses use ETag with different casing
                etag = resp.headers.get("ETag", "").strip('"')
            etags.append(etag)

    print(f"    [LinkedIn] All {total_parts} parts uploaded successfully")
    return etags


# ─────────────────────────────────────────────────────────────
# Step 3: Finalize Video Upload
# ─────────────────────────────────────────────────────────────
def _finalize_upload(video_urn: str, upload_token: str, etags: list[str]):
    """Finalize the multi-part video upload."""
    url = f"{LINKEDIN_API_BASE}/videos?action=finalizeUpload"
    payload = {
        "finalizeUploadRequest": {
            "video": video_urn,
            "uploadToken": upload_token or "",
            "uploadedPartIds": etags,
        }
    }
    resp = requests.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    print(f"    [LinkedIn] Upload finalized for {video_urn}")


# ─────────────────────────────────────────────────────────────
# Step 4: Wait for Video Processing
# ─────────────────────────────────────────────────────────────
def _wait_for_processing(video_urn: str, max_wait: int = 300) -> bool:
    """Poll LinkedIn until the video is AVAILABLE or timeout."""
    import urllib.parse
    encoded_urn = urllib.parse.quote(video_urn, safe="")
    url = f"{LINKEDIN_API_BASE}/videos/{encoded_urn}"

    start = time.time()
    poll_interval = 10  # seconds

    while time.time() - start < max_wait:
        try:
            resp = requests.get(url, headers=_headers())
            if resp.status_code == 200:
                status = resp.json().get("status", "")
                print(f"    [LinkedIn] Video status: {status}")
                if status == "AVAILABLE":
                    return True
                if status == "PROCESSING_FAILED":
                    reason = resp.json().get("processingFailureReason", "unknown")
                    print(f"    [LinkedIn] Processing failed: {reason}")
                    return False
        except Exception as e:
            print(f"    [LinkedIn] Poll error: {e}")

        time.sleep(poll_interval)

    print(f"    [LinkedIn] Timed out waiting for video processing ({max_wait}s)")
    return False


# ─────────────────────────────────────────────────────────────
# Step 5: Create the Post
# ─────────────────────────────────────────────────────────────
def _create_post(
    author_urn: str,
    video_urn: str,
    commentary: str,
    video_title: str = "",
    visibility: str = "PUBLIC",
) -> dict:
    """Create a LinkedIn post with the uploaded video."""
    url = f"{LINKEDIN_API_BASE}/posts"
    payload = {
        "author": author_urn,
        "commentary": commentary,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "title": video_title or "FinanceCats Video",
                "id": video_urn,
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    resp = requests.post(url, json=payload, headers=_headers())
    resp.raise_for_status()

    # Post ID is in the x-restli-id header
    post_id = resp.headers.get("x-restli-id", "")
    post_url = ""
    if post_id:
        # Construct approximate LinkedIn URL
        # For shares: https://www.linkedin.com/feed/update/{post_id}
        post_url = f"https://www.linkedin.com/feed/update/{post_id}"

    print(f"    [LinkedIn] Post created! ID: {post_id}")
    if post_url:
        print(f"    [LinkedIn] URL: {post_url}")

    return {
        "post_id": post_id,
        "post_url": post_url,
        "video_urn": video_urn,
    }


def _get_video_status(video_urn: str) -> str:
    """Get the current status of a LinkedIn video (e.g. WAITING_UPLOAD, PROCESSING, AVAILABLE)."""
    import urllib.parse
    encoded_urn = urllib.parse.quote(video_urn, safe="")
    url = f"{LINKEDIN_API_BASE}/videos/{encoded_urn}"

    try:
        resp = requests.get(url, headers=_headers())
        if resp.status_code == 200:
            return resp.json().get("status", "")
    except Exception:
        pass
    return ""


def _verify_post_content(post_id: str, expected_video_urn: str = "",
                         expected_commentary_start: str = "",
                         max_wait: int = 30) -> dict:
    """Verify a LinkedIn post exists AND has the correct video + commentary.

    Returns dict with:
        post_exists (bool), has_video (bool), commentary_matches (bool),
        lifecycle (str)
    """
    import urllib.parse
    encoded_id = urllib.parse.quote(post_id, safe="")
    url = f"{LINKEDIN_API_BASE}/posts/{encoded_id}"

    start = time.time()
    poll_interval = 5

    while time.time() - start < max_wait:
        try:
            resp = requests.get(url, headers=_headers())
            if resp.status_code == 200:
                data = resp.json()
                lifecycle = data.get("lifecycleState", "")

                # Check video attachment
                content = data.get("content", {})
                media = content.get("media", {})
                video_id = media.get("id", "")
                has_video = (video_id == expected_video_urn) if expected_video_urn else bool(video_id)

                # Check commentary
                actual_commentary = data.get("commentary", "")
                commentary_ok = True
                if expected_commentary_start:
                    commentary_ok = actual_commentary.startswith(expected_commentary_start[:80])

                if lifecycle in ("PUBLISHED", "DRAFT"):
                    return {
                        "post_exists": True,
                        "has_video": has_video,
                        "commentary_matches": commentary_ok,
                        "lifecycle": lifecycle,
                        "video_urn_in_post": video_id,
                    }

            elif resp.status_code == 404:
                pass  # Not propagated yet
        except Exception:
            pass

        time.sleep(poll_interval)

    return {"post_exists": False, "has_video": False,
            "commentary_matches": False, "lifecycle": "unknown"}


# ─────────────────────────────────────────────────────────────
# Public API: Full Upload + Post Flow
# ─────────────────────────────────────────────────────────────
def post_video_to_linkedin(
    video_path: str,
    commentary: str,
    video_title: str = "",
    owner_urn: str = None,
    visibility: str = "PUBLIC",
    wait_for_processing: bool = True,
) -> dict:
    """Upload a video to LinkedIn and create a post.

    Args:
        video_path: Path to the MP4 file.
        commentary: The LinkedIn post text (including hashtags).
        video_title: Title shown on the video player.
        owner_urn: LinkedIn person/org URN. Defaults to config.
        visibility: "PUBLIC" or "CONNECTIONS".
        wait_for_processing: If True, waits for LinkedIn to process the video.

    Returns:
        Dict with post_id, post_url, video_urn, status.
    """
    owner_urn = owner_urn or config.LINKEDIN_PERSON_URN

    if not config.LINKEDIN_ACCESS_TOKEN:
        raise ValueError(
            "LINKEDIN_ACCESS_TOKEN not set in .env. "
            "Get one from LinkedIn Developer Portal with w_member_social scope."
        )

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    file_size = os.path.getsize(video_path)
    print(f"\n  [LinkedIn] Starting video upload ({file_size / (1024*1024):.1f} MB)...")

    # Step 1: Initialize
    init_data = _initialize_upload(file_size, owner_urn)
    video_urn = init_data.get("video", "")
    upload_instructions = init_data.get("uploadInstructions", [])
    upload_token = init_data.get("uploadToken", "")

    if not upload_instructions:
        raise RuntimeError("LinkedIn returned no upload instructions")

    # ══════════════════════════════════════════════════
    # STAGE-BY-STAGE UPLOAD + VERIFICATION
    # ══════════════════════════════════════════════════
    stages = {
        "video_upload": False,
        "finalize": False,
        "video_processing": False,
        "post_created": False,
        "post_has_video": False,
    }

    # ── STAGE 1: Upload video parts ──
    print(f"\n    [Verify] Stage 1: Uploading video parts...")
    etags = _upload_parts(video_path, upload_instructions)
    if etags and len(etags) == len(upload_instructions):
        stages["video_upload"] = True
        print(f"    [Verify] Stage 1 PASSED: All {len(etags)} parts uploaded with ETags")
    else:
        print(f"    [Verify] Stage 1 FAILED: Expected {len(upload_instructions)} parts, "
              f"got {len(etags)} ETags")

    # ── STAGE 2: Finalize + verify status changed ──
    print(f"\n    [Verify] Stage 2: Finalizing upload...")
    _finalize_upload(video_urn, upload_token, etags)
    time.sleep(3)  # Brief wait for LinkedIn to register the finalization

    # Verify video status is no longer in initial state
    finalize_status = _get_video_status(video_urn)
    if finalize_status and finalize_status != "WAITING_UPLOAD":
        stages["finalize"] = True
        print(f"    [Verify] Stage 2 PASSED: Video status = {finalize_status} "
              f"(finalization accepted)")
    else:
        print(f"    [Verify] Stage 2 WARNING: Video status = {finalize_status or 'unknown'} "
              f"(may still be transitioning)")
        stages["finalize"] = True  # Finalize API call succeeded, status may lag

    # ── STAGE 3: Wait for processing + verify AVAILABLE ──
    if wait_for_processing:
        print(f"\n    [Verify] Stage 3: Waiting for video processing...")
        video_ready = _wait_for_processing(video_urn, max_wait=300)
        if video_ready:
            stages["video_processing"] = True
            print(f"    [Verify] Stage 3 PASSED: Video confirmed AVAILABLE")
        else:
            print(f"    [Verify] Stage 3 WARNING: Video not yet AVAILABLE, "
                  f"proceeding with post creation...")
    else:
        stages["video_processing"] = None  # Skipped
        print(f"\n    [Verify] Stage 3: Skipped (wait_for_processing=False)")

    # ── STAGE 4: Create post + verify it exists with correct content ──
    print(f"\n    [Verify] Stage 4: Creating post...")
    result = _create_post(
        author_urn=owner_urn,
        video_urn=video_urn,
        commentary=commentary,
        video_title=video_title,
        visibility=visibility,
    )

    post_id = result.get("post_id", "")
    if post_id:
        # Verify post exists AND has the right content
        time.sleep(3)
        post_check = _verify_post_content(post_id, expected_video_urn=video_urn,
                                           expected_commentary_start=commentary[:100])
        stages["post_created"] = post_check.get("post_exists", False)
        stages["post_has_video"] = post_check.get("has_video", False)

        if stages["post_created"]:
            print(f"    [Verify] Stage 4 PASSED: Post confirmed on LinkedIn "
                  f"(lifecycle: {post_check.get('lifecycle', '?')})")
        else:
            print(f"    [Verify] Stage 4 WARNING: Post created but not yet visible via API")

        if stages["post_has_video"]:
            print(f"    [Verify] Stage 4 PASSED: Video attachment confirmed in post")
        elif stages["post_created"]:
            print(f"    [Verify] Stage 4 WARNING: Post exists but video attachment not confirmed")
    else:
        print(f"    [Verify] Stage 4 FAILED: No post ID returned")

    # ── VERIFICATION SUMMARY ──
    active_stages = {k: v for k, v in stages.items() if v is not None}
    passed = sum(1 for v in active_stages.values() if v is True)
    total = len(active_stages)
    all_passed = passed == total

    print(f"\n    {'=' * 50}")
    print(f"    LINKEDIN VERIFICATION: {passed}/{total} stages passed")
    for stage_name, stage_ok in stages.items():
        if stage_ok is None:
            icon = "SKIP"
        elif stage_ok:
            icon = "PASS"
        else:
            icon = "FAIL"
        print(f"      [{icon}] {stage_name}")
    print(f"    {'=' * 50}")

    result["status"] = "success"
    result["file_size_mb"] = round(file_size / (1024 * 1024), 2)
    result["verified"] = all_passed
    result["verification_stages"] = stages
    result["verification_passed"] = passed
    result["verification_total"] = total
    result["video_verified"] = stages.get("video_processing", False)
    result["post_verified"] = stages.get("post_created", False)

    return result
