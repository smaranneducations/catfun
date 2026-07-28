"""LinkedIn posting with PDF upload support.

Posts the thought leadership brief as a document post on LinkedIn
with proper unicode-formatted text.

Access tokens expire. Prefer LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET +
LINKEDIN_REFRESH_TOKEN in .env so we can refresh; otherwise set a new
LINKEDIN_ACCESS_TOKEN manually when you see EXPIRED_ACCESS_TOKEN.
"""
from __future__ import annotations

import json
import time
import threading
import requests
from pathlib import Path
from aibrief import config


def _persist_linkedin_tokens(updates: dict) -> None:
    """Merge token fields into the JSON file created by setup-linkedin-oauth (optional)."""
    path = getattr(config, "LINKEDIN_OAUTH_TOKEN_FILE", None)
    if not path:
        return
    try:
        p = Path(path)
        existing: dict = {}
        if p.is_file():
            existing = json.loads(p.read_text(encoding="utf-8"))
        existing.update({k: v for k, v in updates.items() if v is not None})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  [LinkedIn OAuth] Could not persist tokens to file: {e}")

API = "https://api.linkedin.com/rest"

_token_lock = threading.Lock()
_cached_access_token: str | None = None
_token_expires_at: float = 0.0


def _invalidate_token_cache() -> None:
    global _cached_access_token, _token_expires_at
    _cached_access_token = None
    _token_expires_at = 0.0


def _oauth_refresh() -> tuple[str | None, int]:
    """Exchange refresh token for access token. Returns (access_token, expires_in)."""
    cid = (config.LINKEDIN_CLIENT_ID or "").strip()
    csec = (config.LINKEDIN_CLIENT_SECRET or "").strip()
    refresh = (config.LINKEDIN_REFRESH_TOKEN or "").strip()
    if not (cid and csec and refresh):
        return None, 0

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": cid,
            "client_secret": csec,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [LinkedIn OAuth] refresh failed: {resp.status_code} — {resp.text[:500]}")
        return None, 0

    data = resp.json()
    access = data.get("access_token")
    expires_in = int(data.get("expires_in", 3600))
    new_refresh = data.get("refresh_token")
    if new_refresh and new_refresh != refresh:
        print(
            "  [LinkedIn OAuth] LinkedIn returned a rotated refresh_token — "
            "saved to linkedin-oauth-token.json if configured."
        )
    if not access:
        return None, 0
    to_save = {"access_token": access, "expires_in": expires_in}
    if new_refresh:
        to_save["refresh_token"] = new_refresh
    _persist_linkedin_tokens(to_save)
    return access, expires_in


def get_effective_linkedin_token(force_refresh: bool = False) -> str:
    """Bearer token for LinkedIn API calls (refreshes when OAuth env is configured)."""
    global _cached_access_token, _token_expires_at

    with _token_lock:
        now = time.time()
        if force_refresh:
            _invalidate_token_cache()

        oauth_configured = bool(
            (config.LINKEDIN_CLIENT_ID or "").strip()
            and (config.LINKEDIN_CLIENT_SECRET or "").strip()
            and (config.LINKEDIN_REFRESH_TOKEN or "").strip()
        )

        if oauth_configured:
            if (
                _cached_access_token
                and now < _token_expires_at - 300
                and not force_refresh
            ):
                return _cached_access_token

            access, expires_in = _oauth_refresh()
            if access:
                _cached_access_token = access
                _token_expires_at = now + max(expires_in, 60)
                print("  [LinkedIn OAuth] Access token obtained via refresh.")
                return access

            static = (config.LINKEDIN_ACCESS_TOKEN or "").strip()
            if static:
                print(
                    "  [LinkedIn OAuth] Refresh failed — falling back to static LINKEDIN_ACCESS_TOKEN "
                    "(may be expired)."
                )
                return static

            raise RuntimeError(
                "LinkedIn OAuth refresh failed and LINKEDIN_ACCESS_TOKEN is not set. "
                "Check LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REFRESH_TOKEN."
            )

        static = (config.LINKEDIN_ACCESS_TOKEN or "").strip()
        if not static:
            raise RuntimeError(
                "LinkedIn not configured: set LINKEDIN_ACCESS_TOKEN, or "
                "LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET + LINKEDIN_REFRESH_TOKEN."
            )
        return static


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_effective_linkedin_token()}",
        "LinkedIn-Version": config.LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _linkedin_request(method: str, url: str, **kwargs) -> requests.Response:
    """Perform request; on 401 EXPIRED_ACCESS_TOKEN, refresh once and retry."""
    kwargs.setdefault("timeout", 30)
    for attempt in range(2):
        hdr = dict(kwargs.pop("headers", {}))
        headers = {**_headers(), **hdr}
        resp = requests.request(method, url, headers=headers, **kwargs)

        if resp.status_code != 401:
            return resp
        if attempt == 1:
            return resp

        try:
            err = resp.json()
            msg = str(err.get("message", ""))
            code = str(err.get("code", ""))
        except Exception:
            msg, code = resp.text[:200], ""

        if "EXPIRED_ACCESS_TOKEN" in msg or "EXPIRED_ACCESS_TOKEN" in code:
            print("  [LinkedIn OAuth] Access token rejected — forcing refresh and retry.")
            _invalidate_token_cache()
            get_effective_linkedin_token(force_refresh=True)
            continue

        return resp


def _upload_pdf(pdf_path: str) -> str:
    """Upload a PDF document to LinkedIn and return the document URN.

    LinkedIn document posts use the /documents API for PDFs.
    """
    print(f"  [LinkedIn] Uploading PDF ({Path(pdf_path).stat().st_size // 1024} KB)...")

    owner_urn = config.LINKEDIN_PERSON_URN
    if not owner_urn.startswith("urn:"):
        owner_urn = f"urn:li:person:{owner_urn}"

    init_payload = {
        "initializeUploadRequest": {
            "owner": owner_urn,
        }
    }
    resp = _linkedin_request(
        "POST",
        f"{API}/documents?action=initializeUpload",
        headers={"Content-Type": "application/json"},
        json=init_payload,
    )

    if resp.status_code != 200:
        print(f"  [LinkedIn] Init failed: {resp.status_code} — {resp.text[:300]}")
        return ""

    data = resp.json().get("value", {})
    upload_url = data.get("uploadUrl", "")
    document_urn = data.get("document", "")

    if not upload_url or not document_urn:
        print(f"  [LinkedIn] No upload URL returned: {data}")
        return ""

    print(f"  [LinkedIn] Document URN: {document_urn}")

    with open(pdf_path, "rb") as f:
        file_data = f.read()

    token = get_effective_linkedin_token()
    upload_resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        data=file_data,
        timeout=120,
    )

    if upload_resp.status_code not in (200, 201):
        print(f"  [LinkedIn] Upload failed: {upload_resp.status_code}")
        return ""

    print("  [LinkedIn] PDF uploaded successfully")
    return document_urn


def _create_text_post(text: str, document_urn: str = "",
                      document_title: str = "") -> dict:
    """Create a LinkedIn post with optional document attachment."""

    author = config.LINKEDIN_PERSON_URN
    if not author.startswith("urn:"):
        author = f"urn:li:person:{author}"

    doc_title = document_title or "AI Strategy Brief"

    if document_urn:
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "visibility": "PUBLIC",
            "commentary": text,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "id": document_urn,
                    "title": doc_title,
                }
            },
        }

        resp = _linkedin_request(
            "POST",
            f"{API}/posts",
            headers={"Content-Type": "application/json"},
            json=payload,
        )

        if resp.status_code in (200, 201):
            post_id = resp.headers.get("x-restli-id", resp.text.strip('"'))
            url = f"https://www.linkedin.com/feed/update/{post_id}"
            print(f"  [LinkedIn] Document post created: {url}")
            return {"status": "success", "post_id": post_id, "url": url}
        else:
            print(f"  [LinkedIn] Document post failed: {resp.status_code}")
            print(f"  [LinkedIn] {resp.text[:300]}")
            print("  [LinkedIn] Trying text-only post...")

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
    }

    resp = _linkedin_request(
        "POST",
        "https://api.linkedin.com/v2/ugcPosts",
        headers={"Content-Type": "application/json"},
        json=payload,
    )

    if resp.status_code in (200, 201):
        post_id = resp.json().get("id", "")
        url = f"https://www.linkedin.com/feed/update/{post_id}"
        print(f"  [LinkedIn] Text post created: {url}")
        return {"status": "success", "post_id": post_id, "url": url}
    else:
        print(f"  [LinkedIn] Text post failed: {resp.status_code}")
        print(f"  [LinkedIn] Response: {resp.text[:500]}")
        return {"status": "failed", "error": resp.text[:500]}


def post_brief(pdf_path: str, post_text: str, story: dict = None,
               document_title: str = None) -> dict:
    """Upload PDF to LinkedIn and create a document post.

    Falls back to text-only post if PDF upload fails.
    After successful post, stores embedding for semantic dedup.

    Args:
        document_title: Catchy, topic-specific title shown in LinkedIn's
                       carousel view. Should be attention-grabbing, NOT generic.
    """
    print("\n  [LinkedIn] Starting post...")
    try:
        get_effective_linkedin_token()
    except RuntimeError as e:
        return {"status": "failed", "error": str(e), "url": "", "post_id": ""}

    if document_title:
        print(f"  [LinkedIn] Document title: {document_title}")

    doc_urn = _upload_pdf(pdf_path)

    result = None
    if doc_urn:
        result = _create_text_post(post_text, document_urn=doc_urn,
                                   document_title=document_title or "")
        if result.get("status") != "success":
            result = None

    if not result:
        print("  [LinkedIn] Falling back to text-only post...")
        result = _create_text_post(post_text)

    if result.get("status") == "success" and story:
        try:
            from aibrief.pipeline.dedup import store_embedding
            store_embedding(story, post_id=result.get("post_id", ""))
        except Exception as e:
            print(f"  [LinkedIn] Embedding storage error (non-fatal): {e}")

    return result
