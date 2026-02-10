"""LinkedIn posting with PDF upload support.

Posts the thought leadership brief as a document post on LinkedIn
with proper unicode-formatted text.
"""
import json
import time
import requests
from pathlib import Path
from aibrief import config

API = "https://api.linkedin.com/rest"
HEADERS = {
    "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
    "LinkedIn-Version": config.LINKEDIN_API_VERSION,
    "X-Restli-Protocol-Version": "2.0.0",
}


def _upload_pdf(pdf_path: str) -> str:
    """Upload a PDF document to LinkedIn and return the document URN.

    LinkedIn document posts use the /documents API for PDFs.
    """
    print(f"  [LinkedIn] Uploading PDF ({Path(pdf_path).stat().st_size // 1024} KB)...")

    # Step 1: Initialise document upload
    # Use the full person URN as-is
    owner_urn = config.LINKEDIN_PERSON_URN
    if not owner_urn.startswith("urn:"):
        owner_urn = f"urn:li:person:{owner_urn}"

    init_payload = {
        "initializeUploadRequest": {
            "owner": owner_urn,
        }
    }
    resp = requests.post(
        f"{API}/documents?action=initializeUpload",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=init_payload,
        timeout=30,
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

    # Step 2: Upload the actual file
    with open(pdf_path, "rb") as f:
        file_data = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream",
        },
        data=file_data,
        timeout=120,
    )

    if upload_resp.status_code not in (200, 201):
        print(f"  [LinkedIn] Upload failed: {upload_resp.status_code}")
        return ""

    print(f"  [LinkedIn] PDF uploaded successfully")
    return document_urn


def _create_text_post(text: str, document_urn: str = "",
                      document_title: str = "") -> dict:
    """Create a LinkedIn post with optional document attachment."""

    author = config.LINKEDIN_PERSON_URN
    if not author.startswith("urn:"):
        author = f"urn:li:person:{author}"

    # Dynamic, catchy document title — never generic "AI Strategy Brief"
    doc_title = document_title or "AI Strategy Brief"

    # Try the newer /posts API first (supports documents natively)
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

        resp = requests.post(
            f"{API}/posts",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            # The /posts API returns the post ID in x-restli-id header
            post_id = resp.headers.get("x-restli-id", resp.text.strip('"'))
            url = f"https://www.linkedin.com/feed/update/{post_id}"
            print(f"  [LinkedIn] Document post created: {url}")
            return {"status": "success", "post_id": post_id, "url": url}
        else:
            print(f"  [LinkedIn] Document post failed: {resp.status_code}")
            print(f"  [LinkedIn] {resp.text[:300]}")
            print(f"  [LinkedIn] Trying text-only post...")

    # Fallback: text-only post via UGC API
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

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
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
    if document_title:
        print(f"  [LinkedIn] Document title: {document_title}")

    # Try document post first
    doc_urn = _upload_pdf(pdf_path)

    result = None
    if doc_urn:
        result = _create_text_post(post_text, document_urn=doc_urn,
                                   document_title=document_title or "")
        if result.get("status") != "success":
            result = None

    if not result:
        # Fallback: text-only post
        print("  [LinkedIn] Falling back to text-only post...")
        result = _create_text_post(post_text)

    # Store embedding for future semantic dedup
    if result.get("status") == "success" and story:
        try:
            from aibrief.pipeline.dedup import store_embedding
            store_embedding(story, post_id=result.get("post_id", ""))
        except Exception as e:
            print(f"  [LinkedIn] Embedding storage error (non-fatal): {e}")

    return result
