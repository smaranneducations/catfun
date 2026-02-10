"""Central configuration for FinanceCats — AI Finance Education Video Generator."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
CATS_DIR = os.path.join(ASSETS_DIR, "cats", "repository")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
EPISODE_LOG_PATH = os.path.join(BASE_DIR, "episode_log.json")

# --- LLM Settings ---
LLM_MODEL = "gpt-4o"            # Primary model for complex tasks
LLM_MODEL_MINI = "gpt-4o-mini"  # Cost-effective for lighter tasks

# --- Video Settings ---
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
MIN_VIDEO_DURATION = 240   # 4 minutes
MAX_VIDEO_DURATION = 390   # 6.5 minutes

# --- Video Segment Ranges (seconds) ---
SEGMENT_NEWS_INTRO = (10, 20)       # First news clip
SEGMENT_CAT_INTRO = (20, 40)        # "Watch for this..."
SEGMENT_NEWS_CONTEXT = (20, 40)     # News clip again
SEGMENT_LECTURE = (120, 200)        # The education section
SEGMENT_NEWS_FINAL = (15, 25)       # Last bit of news
SEGMENT_CAT_WRAPUP = (15, 25)      # Wrap-up + tease

# --- ElevenLabs Voice Settings ---
# "Daniel" - calm, clear British accent — perfect for finance education
NARRATOR_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# --- Cat Repository ---
TOTAL_CATS = 30  # Number of cat images in repository

# --- Background Music ---
MUSIC_VOLUME = 0.12  # 12% volume relative to voice (subtle)

# --- Ensure directories exist ---
for d in [OUTPUT_DIR, TEMP_DIR, CATS_DIR, MUSIC_DIR]:
    os.makedirs(d, exist_ok=True)
