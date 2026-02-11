"""Configuration for AI Brief — AI Thought Leadership PDF + LinkedIn Publisher."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (shared with catfun)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
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

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

