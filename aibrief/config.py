"""Configuration for AI Brief — AI Thought Leadership PDF + LinkedIn Publisher."""
from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env from parent directory (shared with catfun)
load_dotenv(REPO_ROOT / ".env")


def _env_nonempty(key: str) -> str | None:
    v = os.getenv(key)
    return v.strip() if v and str(v).strip() else None


def _load_linkedin_token_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# LinkedIn: tokens from .env override tokens saved by `npm run setup-linkedin-oauth` (JSON file).
_tfp = _env_nonempty("LINKEDIN_OAUTH_TOKEN_FILE")
LINKEDIN_OAUTH_TOKEN_FILE = Path(_tfp) if _tfp else (REPO_ROOT / "temp" / "linkedin-oauth-token.json")
_linkedin_file = _load_linkedin_token_file(LINKEDIN_OAUTH_TOKEN_FILE)

LINKEDIN_ACCESS_TOKEN = _env_nonempty("LINKEDIN_ACCESS_TOKEN") or _linkedin_file.get("access_token")
# OAuth 2.0 — CLIENT_ID + CLIENT_SECRET + REFRESH_TOKEN refresh automatically (error 65602).
LINKEDIN_CLIENT_ID = _env_nonempty("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = _env_nonempty("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REFRESH_TOKEN = _env_nonempty("LINKEDIN_REFRESH_TOKEN") or _linkedin_file.get("refresh_token")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "urn:li:person:Ah-ZXoM8LR")
LINKEDIN_API_VERSION = "202601"

# --- Model Assignment ---
# GPT-4o for quality-critical tasks
MODEL_CONTENT_WRITER = "gpt-4o"
MODEL_EDITOR_IN_CHIEF = "gpt-4o"
MODEL_CONTENT_REVIEWER = "gpt-4o"
MODEL_LINKEDIN_EXPERT = "gpt-4o"

# Gemini Flash for cheaper analytical tasks
MODEL_NEWS_SCOUT = "gemini-2.0-flash"
MODEL_HISTORIAN = "gemini-2.0-flash"
MODEL_ECONOMIST = "gemini-2.0-flash"
MODEL_SOCIOLOGIST = "gemini-2.0-flash"
MODEL_FUTURIST = "gemini-2.0-flash"
# Phase 0: World Pulse (cheap real-time scan)
MODEL_WORLD_PULSE = "gemini-2.0-flash"

# Phase 1: Content Strategy (needs higher reasoning — strategic decision)
MODEL_CONTENT_STRATEGIST = "gpt-4o"

# Phase 2: Design DNA (needs creative reasoning — visual identity)
MODEL_DESIGN_DNA = "gpt-4o"

# Phase 8.5: Discussion Potential (engagement analysis — needs reasoning)
MODEL_DISCUSSION_POTENTIAL = "gpt-4o"

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

