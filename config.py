"""Central configuration for FinanceCats — AI Finance Education Video Generator.

V3: AI News Anchor + Cat Conversation format.
  - DALL-E generates animated anchor image
  - ElevenLabs TTS voices the anchor script
  - Animated effects (zoom, news graphics) bring it to life
  - Cats explain the financial term embedded in the news
  - 100% original content — no third-party clips
  - Gemini Flash for cheap tasks, GPT-4o for critical tasks
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# LinkedIn
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "urn:li:person:Ah-ZXoM8LR")
LINKEDIN_API_VERSION = "202601"  # YYYYMM format

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
CATS_DIR = os.path.join(ASSETS_DIR, "cats", "repository")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
ANCHOR_DIR = os.path.join(ASSETS_DIR, "anchors")
EPISODE_LOG_PATH = os.path.join(BASE_DIR, "episode_log.json")

# --- LLM Settings ---
# GPT-4o for critical tasks (script writing, executive approval)
LLM_MODEL = "gpt-4o"

# Gemini Flash for cheaper tasks (news scout, fact checker, analysts)
# ~25x cheaper than GPT-4o for input tokens
LLM_MODEL_GEMINI = "gemini-2.0-flash"

# Gemini Pro for medium-complexity tasks (if needed)
LLM_MODEL_GEMINI_PRO = "gemini-2.0-flash"  # Flash is good enough for most

# Cost-effective OpenAI model (legacy, use Gemini Flash instead)
LLM_MODEL_MINI = "gpt-4o-mini"

# --- Model Assignment (which agent uses which model) ---
# Critical tasks → GPT-4o (best JSON output, script quality)
MODEL_SCRIPT_WRITER = LLM_MODEL           # anchor + cat scripts need quality
MODEL_EXECUTIVE_PRODUCER = LLM_MODEL      # brand decisions need quality

# Cheaper tasks → Gemini Flash (25x cheaper, still good)
MODEL_VIRAL_NEWS_SCOUT = LLM_MODEL_GEMINI     # finding news is straightforward
MODEL_FINANCIAL_HISTORIAN = LLM_MODEL_GEMINI   # research is fact-heavy, Flash is fine
MODEL_SOCIOLOGICAL_ANALYST = LLM_MODEL_GEMINI  # optional specialist
MODEL_GEOPOLITICAL_ANALYST = LLM_MODEL_GEMINI  # optional specialist
MODEL_FACT_CHECKER = LLM_MODEL_GEMINI          # checking facts, Flash is fine
MODEL_CREATIVE_DIRECTOR = LLM_MODEL_GEMINI     # cat selection is simple
MODEL_YOUTUBE_STRATEGIST = LLM_MODEL_GEMINI    # SEO package, Flash is fine
MODEL_LINKEDIN_STRATEGIST = LLM_MODEL_GEMINI   # post copy, Flash is fine

# --- Video Settings ---
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

# V3: Shorter videos (3-4 minutes total)
MIN_VIDEO_DURATION = 180   # 3 minutes
MAX_VIDEO_DURATION = 270   # 4.5 minutes (some buffer)

# --- V3 Video Segment Durations (seconds) ---
SEGMENT_ANCHOR_NEWS = (60, 90)         # Anchor reads news: 60-90 seconds
SEGMENT_CAT_CONVERSATION = (120, 180)  # Cat explanation: 2-3 minutes

# --- V3 Anchor Settings ---
# The anchor always starts with: "OK, this news is from [date]..."
ANCHOR_INTRO_TEMPLATE = "OK, this news is from {date}."

# DALL-E prompt for generating the animated anchor image
# Attractive female, professional, animated style, high-end studio
ANCHOR_IMAGE_PROMPT = (
    "An attractive professional female news anchor sitting at a modern "
    "high-end TV news studio desk, animated illustration style, clean lines, "
    "warm lighting, wearing a stylish dark blazer, confident and friendly "
    "expression, looking directly at camera, studio monitors and screens "
    "in background with financial data, soft bokeh lights, broadcast quality, "
    "16:9 widescreen composition, the anchor is on the left side of frame "
    "leaving space on the right side. Professional but approachable, "
    "NOT photorealistic — clean animated/illustrated style."
)

# Anchor voice: use a warm, professional female voice from ElevenLabs
# Reusing Cat B's voice (Charlotte) — warm British female — for the anchor
ANCHOR_VOICE_ID = "XB0fDUnXU5powFXDhCwa"  # Charlotte (warm British female)

# Animation settings for the anchor segment
ANCHOR_ZOOM_SPEED = 0.0008   # Slow zoom per frame (subtle Ken Burns effect)
ANCHOR_PAN_SPEED = 0.0003    # Slow pan per frame

# --- Viral News Settings ---
VIRAL_NEWS_LOOKBACK_DAYS = 7  # Look for viral news from last 7 days

# --- ElevenLabs Voice Settings ---
# Cat A — "Professor" — the explainer (Daniel: calm, clear British male accent)
CAT_A_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"   # Daniel
CAT_A_NAME = "Professor Whiskers"

# Cat B — "Curious" — the questioner (Charlotte: warm, curious British female)
CAT_B_VOICE_ID = "XB0fDUnXU5powFXDhCwa"   # Charlotte
CAT_B_NAME = "Cleo"

ELEVENLABS_MODEL = "eleven_multilingual_v2"

# Legacy alias
NARRATOR_VOICE_ID = CAT_A_VOICE_ID

# --- Series Settings ---
DEFAULT_SERIES_LENGTH = 10
MAX_SERIES_LENGTH = 15

# --- Cat Repository ---
TOTAL_CATS = 30

# --- Background Music ---
MUSIC_VOLUME = 0.12

# --- Ensure directories exist ---
for d in [OUTPUT_DIR, TEMP_DIR, CATS_DIR, MUSIC_DIR, ANCHOR_DIR]:
    os.makedirs(d, exist_ok=True)
