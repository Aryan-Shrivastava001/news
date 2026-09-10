import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
AUDIO_DIR = ASSETS_DIR / "audio"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_FILE = BASE_DIR / "posted_history.json"

# Ensure runtime directories exist
for folder in [ASSETS_DIR, SPRITES_DIR, AUDIO_DIR, BACKGROUNDS_DIR, OUTPUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# API Keys & Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "ErXwobaYiN019PkySvjV") # Default: Antoni / Energetic narrator

# Fallback Edge-TTS Voice
DEFAULT_EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-ChristopherNeural")

# YouTube API Credentials
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")

# Video Specs (YouTube Shorts Vertical)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
MAX_SHORT_DURATION = 55 # seconds
TARGET_WORD_COUNT = 85 # ~35-42 seconds speech

# News Configuration
NEWS_WINDOW_HOURS = int(os.getenv("NEWS_WINDOW_HOURS", "4"))
